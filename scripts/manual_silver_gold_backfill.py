import duckdb
import os
import pandas as pd
import argparse
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv


def get_duckdb_con():
    con = duckdb.connect(database=":memory:")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")

    if all([aws_key, aws_secret, aws_region]):
        con.execute("INSTALL httpfs;")
        con.execute("LOAD httpfs;")
        con.execute(f"SET s3_region='{aws_region}';")
        con.execute(f"SET s3_access_key_id='{aws_key}';")
        con.execute(f"SET s3_secret_access_key='{aws_secret}';")
    return con


def backfill_silver_gold(target_dates):
    """
    Backfills the Silver and Gold layers strictly following Medallion architecture.
    """
    bucket = os.getenv("S3_BUCKET_NAME")
    if not bucket:
        print("[ERROR] S3_BUCKET_NAME is not set. Cannot run backfill.")
        return

    con = get_duckdb_con()

    for date_str in target_dates:
        print("==================================================")
        print(f"Starting pipeline backfill for {date_str}...")
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            year = target_date.strftime("%Y")
            month = target_date.strftime("%m")
            day = target_date.strftime("%d")

            # Corrected paths: Only use the active DLT bronze path
            dlt_path = (
                f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
            )

            silver_dir = f"s3://{bucket}/silver/year={year}/month={month}/day={day}"
            silver_path = f"{silver_dir}/clean_prices_{date_str}.parquet"

            gold_dir = f"s3://{bucket}/gold/year={year}/month={month}/day={day}"
            gold_path = f"{gold_dir}/regional_kpis_{date_str}.parquet"

            # STEP A: MATERIALIZE SILVER
            print(f"-> Step A: Materializing Silver layer to {silver_path}...")

            # Note: The raw data contains extract_dt and commodity_group, commodity_name.
            # We map commodity_group -> category and commodity_name -> commodity
            # to meet Streamlit's expectations.
            from src.core.config import REGION_MAP

            cases = []
            for rid, rname in REGION_MAP.items():
                cases.append(
                    f"WHEN LPAD(CAST(TRY_CAST(region_name AS BIGINT) AS VARCHAR), 9, '0') = '{rid}' THEN '{rname}'"
                )
            case_sql = "CASE " + " ".join(cases) + " ELSE region_name END"

            silver_query = f"""
            COPY (
                WITH source as (
                    SELECT * FROM read_parquet('{dlt_path}', union_by_name=true)
                ),
                silver as (
                    SELECT
                        {case_sql} as region_name,
                        market_name,
                        commodity_group as category,
                        commodity_name as commodity,
                        try_cast(price as double) as price,
                        try_cast(extract_dt as timestamp) as extract_dt
                    FROM source
                    WHERE CAST(extract_dt AS DATE) = '{date_str}'
                )
                SELECT * FROM silver
                WHERE price <= 20000 AND price >= 0
            ) TO '{silver_path}' (FORMAT 'parquet', OVERWRITE_OR_IGNORE true);
            """

            con.execute(silver_query)
            print(f"   [SUCCESS] Silver materialized for {date_str}.")

            # STEP B: MATERIALIZE GOLD
            print(
                f"-> Step B: Materializing Gold layer to {gold_path} from Silver data..."
            )
            gold_query = f"""
            COPY (
                SELECT
                    region_name,
                    commodity,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    CASE
                        WHEN AVG(price) > 0 THEN ((MAX(price) - MIN(price)) / AVG(price)) * 100
                        ELSE 0
                    END as price_volatility,
                    MAX(extract_dt) as latest_date,
                    0 as days_ago
                FROM read_parquet('{silver_path}')
                WHERE region_name IS NOT NULL AND commodity IS NOT NULL
                GROUP BY region_name, commodity
            ) TO '{gold_path}' (FORMAT 'parquet', OVERWRITE_OR_IGNORE true);
            """

            con.execute(gold_query)
            print(f"   [SUCCESS] Gold materialized for {date_str}.")

        except Exception as e:
            print(f"[ERROR] Failed to process {date_str}: {e}")

    con.close()
    print("==================================================")
    print("Backfill process complete.")


def generate_date_range(start_date_str, end_date_str):
    """Generates a list of YYYY-MM-DD strings between start and end (inclusive)."""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

    delta = end_dt - start_dt
    if delta.days < 0:
        return []

    return [
        (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(delta.days + 1)
    ]


if __name__ == "__main__":
    load_dotenv()
    pht_tz = ZoneInfo("Asia/Manila")
    pht_now = datetime.now(pht_tz)

    parser = argparse.ArgumentParser(
        description="Medallion Architecture Backfill Orchestrator"
    )
    parser.add_argument("--start-date", help="Backfill start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Backfill end date (YYYY-MM-DD)")
    parser.add_argument(
        "--all", action="store_true", help="Backfill entire history from Bronze layer"
    )

    args = parser.parse_args()
    bucket = os.getenv("S3_BUCKET_NAME")

    target_dates = []

    if args.all:
        if not bucket:
            print("[ERROR] S3_BUCKET_NAME required for --all scan.")
            sys.exit(1)

        print("-> Scanning Bronze metadata for historical bounds...")
        con = get_duckdb_con()
        bronze_path = (
            f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
        )
        try:
            # Efficiently query min/max dates from S3 metadata
            bounds_query = f"SELECT MIN(CAST(extract_dt AS DATE)) as min_dt, MAX(CAST(extract_dt AS DATE)) as max_dt FROM read_parquet('{bronze_path}')"
            df = con.sql(bounds_query).df()
            if not df.empty and pd.notnull(df.iloc[0]["min_dt"]):
                start = df.iloc[0]["min_dt"].strftime("%Y-%m-%d")
                end = df.iloc[0]["max_dt"].strftime("%Y-%m-%d")
                print(f"   [INFO] Found history: {start} to {end}")
                target_dates = generate_date_range(start, end)
            else:
                print("[WARNING] No data found in Bronze layer.")
        except Exception as e:
            print(f"[ERROR] Historical scan failed: {e}")
            sys.exit(1)
        finally:
            con.close()
    elif args.start_date:
        start = args.start_date
        end = args.end_date if args.end_date else pht_now.strftime("%Y-%m-%d")
        target_dates = generate_date_range(start, end)
    else:
        # Default behavior: Today's date (PHT)
        target_dates = [pht_now.strftime("%Y-%m-%d")]

    if not target_dates:
        print("[INFO] No dates to process.")
    else:
        print(f"[INFO] Prepared {len(target_dates)} days for backfill.")
        backfill_silver_gold(target_dates)
