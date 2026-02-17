import os

import duckdb
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Framework Imports
from src.core.config import REGION_MAP
from src.utils.logger import get_logger

# Load Environment Variables
load_dotenv()

# Initialize Logger
logger = get_logger(__name__)


def get_latest_date_str():
    """Returns today's date in YYYY-MM-DD format for default processing."""
    return datetime.now().strftime("%Y-%m-%d")


def setup_duckdb(con):
    """Configures DuckDB with AWS credentials and httpfs."""
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION")

    if not all([aws_key, aws_secret, aws_region]):
        logger.error("Missing AWS Credentials in environment variables.")
        raise ValueError("Missing AWS Credentials")

    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute(f"SET s3_region='{aws_region}';")
    con.execute(f"SET s3_access_key_id='{aws_key}';")
    con.execute(f"SET s3_secret_access_key='{aws_secret}';")

    # Optional: Increase timeout or retries if needed
    # con.execute("SET s3_url_style='path';")


def run_transform(target_date=None):
    """
    Orchestrates the S3-based Lakehouse transformation pipeline.
    Bronze (S3) -> Silver (S3 Parquet) -> Gold (S3 Parquet)
    """
    start_time = datetime.now()
    logger.info("START: Lakehouse Transformation Pipeline")

    if not target_date:
        target_date = get_latest_date_str()

    # Parse Date
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        year, month, day = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    except ValueError:
        logger.error(f"Invalid date format: {target_date}. Expected YYYY-MM-DD.")
        return

    s3_bucket = os.getenv("S3_BUCKET_NAME")
    if not s3_bucket:
        logger.error("S3_BUCKET_NAME not set.")
        return

    # Paths (Deep Partitioning)
    bronze_path = f"s3://{s3_bucket}/bronze/year={year}/month={month}/day={day}/*.csv"
    silver_path = f"s3://{s3_bucket}/silver/year={year}/month={month}/day={day}/clean_prices.parquet"  # noqa: E501
    gold_path = f"s3://{s3_bucket}/gold/year={year}/month={month}/day={day}/regional_kpis.parquet"  # noqa: E501

    con = duckdb.connect(database=":memory:")

    try:
        setup_duckdb(con)

        # --- SILVER LAYER ---
        logger.info("Processing Silver Layer...", source=bronze_path)

        # Register Region Map for enrichment
        # Normalize keys as string
        # (Assuming CSV region_id is read as int/string, we cast to string in SQL)
        region_df = pd.DataFrame(
            list(REGION_MAP.items()), columns=["region_id", "region_name"]
        )
        con.register("region_map", region_df)

        silver_query = f"""
        WITH raw_data AS (
            SELECT
                extract_dt,
                CAST(region_id AS VARCHAR) as region_id_raw,
                market_name,
                category,
                commodity,
                CAST(price AS DOUBLE) as price
            FROM read_csv_auto('{bronze_path}', header=True, union_by_name=true)
        ),
        enriched AS (
            SELECT
                r.extract_dt,
                r.market_name,
                r.category,
                r.commodity,
                r.price,
                COALESCE(m.region_name, r.region_id_raw) as region_name,
                md5(concat(r.extract_dt, r.region_id_raw, r.commodity, r.market_name)) as record_id
            FROM raw_data r
            LEFT JOIN region_map m ON r.region_id_raw = m.region_id
        ),
        deduped AS (
            SELECT *
            FROM (
                SELECT
                    *,
                    row_number() OVER (
                        PARTITION BY record_id ORDER BY extract_dt DESC
                    ) as rn
                FROM enriched
            )
            WHERE rn = 1
        )
        SELECT
            extract_dt,
            region_name,
            market_name,
            category,
            commodity,
            price
        FROM deduped
        """

        # Debug: Check if data exists
        # Just strict copy
        con.execute(
            f"COPY ({silver_query}) TO '{silver_path}' "
            "(FORMAT PARQUET, OVERWRITE_OR_IGNORE true)"
        )
        logger.info("Silver Layer Written", path=silver_path)

        # --- GOLD LAYER ---
        logger.info("Processing Gold Layer...")

        gold_query = f"""
        SELECT
            region_name,
            commodity,
            AVG(price) as avg_price,
            MAX(price) - MIN(price) as price_volatility,
            MAX(extract_dt) as latest_date
        FROM read_parquet('{silver_path}')
        GROUP BY region_name, commodity
        ORDER BY region_name, commodity
        """

        con.execute(
            f"COPY ({gold_query}) TO '{gold_path}' "
            "(FORMAT PARQUET, OVERWRITE_OR_IGNORE true)"
        )
        logger.info("Gold Layer Written", path=gold_path)

    except Exception as e:
        logger.error("S3 Pipeline Failed. Initiating Local Fallback...", error=str(e))

        # --- LOCAL FALLBACK (Strict Hive Partitioning) ---
        try:
            # Paths (Local)
            # data/clean/year={YYYY}/month={MM}/day={DD}/
            local_clean_dir = f"data/clean/year={year}/month={month}/day={day}"
            local_gold_dir = f"data/gold/year={year}/month={month}/day={day}"

            os.makedirs(local_clean_dir, exist_ok=True)
            os.makedirs(local_gold_dir, exist_ok=True)

            local_silver_path = f"{local_clean_dir}/market_prices.parquet"
            local_gold_path = f"{local_gold_dir}/regional_kpis.parquet"

            # Check if silver_query was successful (it tries to write to S3).
            # If it failed, we try to run the SAME query but write locally.

            logger.info("Attempting Local Silver Write...")
            con.execute(
                f"COPY ({silver_query}) TO '{local_silver_path}' (FORMAT PARQUET)"
            )
            logger.info("Local Silver Layer Written", path=local_silver_path)

            logger.info("Attempting Local Gold Write...")
            # Gold needs to read from the JUST WRITTEN Silver.
            # If S3 write failed, we read from LOCAL Silver.

            gold_query_local = f"""
            SELECT
                region_name,
                commodity,
                AVG(price) as avg_price,
                MAX(price) - MIN(price) as price_volatility,
                MAX(extract_dt) as latest_date
            FROM read_parquet('{local_silver_path}')
            GROUP BY region_name, commodity
            ORDER BY region_name, commodity
            """
            con.execute(
                f"COPY ({gold_query_local}) TO '{local_gold_path}' " "(FORMAT PARQUET)"
            )
            logger.info("Local Gold Layer Written", path=local_gold_path)

        except Exception as local_e:
            logger.error("CRITICAL: Local Fallback Failed", error=str(local_e))
            import traceback

            traceback.print_exc()

    finally:
        con.close()
        duration = datetime.now() - start_time
        logger.info("Pipeline Finished", duration=str(duration))


def discover_bronze_dates(s3_bucket):
    """Scans S3 Bronze layer partitions to find all available dates."""
    import boto3
    from collections import defaultdict
    
    try:
        s3 = boto3.client('s3')
        logger.info("Discovering Bronze dates via S3 partitions...")
        
        # List all objects in Bronze layer
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=s3_bucket, Prefix='bronze/')
        
        dates_set = set()
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                # Parse path: bronze/year=2026/month=02/day=09/file.csv
                if '/day=' in key:
                    parts = key.split('/')
                    year = month = day = None
                    
                    for part in parts:
                        if part.startswith('year='):
                            year = part.split('=')[1]
                        elif part.startswith('month='):
                            month = part.split('=')[1]
                        elif part.startswith('day='):
                            day = part.split('=')[1]
                    
                    if year and month and day:
                        date_str = f"{year}-{month}-{day}"
                        dates_set.add(date_str)
        
        # Convert to datetime objects and sort
        dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in dates_set])
        
        logger.info(f"Discovered {len(dates)} dates in Bronze", dates=[d.strftime("%Y-%m-%d") for d in dates])
        
        return dates
    except Exception as e:
        logger.error(f"Failed to discover Bronze dates: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_backfill():
    """Processes all available Bronze dates into Silver/Gold."""
    logger.info("START: Backfill Mode")
    
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    if not s3_bucket:
        logger.error("S3_BUCKET_NAME not set")
        return False
    
    dates = discover_bronze_dates(s3_bucket)
    
    if not dates:
        logger.warning("No dates found to backfill")
        return False
    
    success_count = 0
    failed_dates = []
    
    for date_obj in dates:
        date_str = date_obj.strftime("%Y-%m-%d")
        logger.info(f"Processing backfill for {date_str}")
        
        if run_transform(target_date=date_str):
            success_count += 1
        else:
            failed_dates.append(date_str)
    
    logger.info(
        "COMPLETE: Backfill",
        total=len(dates),
        success=success_count,
        failed=len(failed_dates),
        failed_dates=failed_dates
    )
    
    return len(failed_dates) == 0


if __name__ == "__main__":
    import sys
    
    if "--backfill" in sys.argv:
        success = run_backfill()
    else:
        success = run_transform()
    
    sys.exit(0 if success else 1)
