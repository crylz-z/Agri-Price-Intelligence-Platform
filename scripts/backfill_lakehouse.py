import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

if not all(
    [S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION]
):
    print("[ERROR] Environment variables missing. Ensure .env is loaded.")
    exit(1)


def setup_duckdb(con):
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute(f"SET s3_region='{AWS_DEFAULT_REGION}';")
    con.execute(f"SET s3_access_key_id='{AWS_ACCESS_KEY_ID}';")
    con.execute(f"SET s3_secret_access_key='{AWS_SECRET_ACCESS_KEY}';")


def run_backfill():
    print("[INFO] Starting Lakehouse Backfill...")
    con = duckdb.connect(database=":memory:")
    setup_duckdb(con)

    # 1. Bronze Path (Source)
    # Assumes structure: s3://bucket/bronze/year=*/month=*/day=*/files.csv
    # But user prompt said "reads all historical CSVs from the S3 Bronze layer"
    bronze_glob = f"s3://{S3_BUCKET_NAME}/bronze/year=*/month=*/day=*/*.csv"

    # 2. Silver Query (Enrich & Dedupe)
    # Extract date from filepath or content ideally, but let's assume content has extract_dt
    print(f"[INFO] Reading Bronze Data from: {bronze_glob}")

    try:
        # Silver Layer Logic
        silver_query = f"""
        WITH raw_data AS (
            SELECT 
                extract_dt,
                region_id as region_id_raw,
                market_name,
                category,
                commodity,
                TRY_CAST(price AS DOUBLE) as price,
                filename
            FROM read_csv('{bronze_glob}', header=True, filename=true, all_varchar=true)
            WHERE TRY_CAST(price AS DOUBLE) IS NOT NULL
        ),
        enriched AS (
            SELECT 
                r.*,
                -- Simple region lookup or passthrough if Map absent
                r.region_id_raw as region_name, 
                md5(concat(extract_dt, region_id_raw, commodity, market_name)) as record_id
            FROM raw_data r
        ),
        deduped AS (
            SELECT * 
            FROM (
                SELECT 
                    *,
                    row_number() OVER (PARTITION BY record_id ORDER BY extract_dt DESC) as rn
                FROM enriched
            )
            WHERE rn = 1
        )
        SELECT 
            extract_dt,
            region_name,
            market_name,
            commodity,
            price
            -- We need year/month/day columns for partitioning
            ,strftime(cast(extract_dt as date), '%Y') as year
            ,strftime(cast(extract_dt as date), '%m') as month
            ,strftime(cast(extract_dt as date), '%d') as day
        FROM deduped
        """

        silver_path = f"s3://{S3_BUCKET_NAME}/silver/"
        print("[INFO] processing Silver Layer...")
        con.execute(
            f"""
            COPY ({silver_query}) 
            TO '{silver_path}' 
            (FORMAT PARQUET, PARTITION_BY (year, month, day), OVERWRITE_OR_IGNORE true)
        """
        )
        print(f"[INFO] Silver Layer written to {silver_path}")

        # Gold Query (Aggregates)
        # Read from the JUST WRITTEN Silver files
        gold_query = f"""
        SELECT 
            region_name,
            commodity,
            AVG(price) as avg_price,
            MAX(price) - MIN(price) as price_volatility,
            MAX(extract_dt) as latest_date,
            strftime(cast(MAX(extract_dt) as date), '%Y') as year,
            strftime(cast(MAX(extract_dt) as date), '%m') as month,
            strftime(cast(MAX(extract_dt) as date), '%d') as day
        FROM read_parquet('{silver_path}*/*/*/*.parquet', hive_partitioning=true)
        GROUP BY region_name, commodity
        """

        gold_path = f"s3://{S3_BUCKET_NAME}/gold/"
        print("[INFO] processing Gold Layer...")
        con.execute(
            f"""
            COPY ({gold_query}) 
            TO '{gold_path}' 
            (FORMAT PARQUET, PARTITION_BY (year, month, day), OVERWRITE_OR_IGNORE true)
        """
        )
        print(f"[INFO] Gold Layer written to {gold_path}")

    except Exception as e:
        print(f"[ERROR] Backfill failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        con.close()
        print("[INFO] Backfill Complete.")


if __name__ == "__main__":
    run_backfill()
