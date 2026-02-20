import duckdb
import os
from datetime import datetime
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

def backfill_gold(target_dates):
    """
    Backfills the Gold layer for the provided target dates.
    Reads from the Silver layer, aggregates to regional KPIs, and writes to Gold.
    """
    load_dotenv()
    bucket = os.getenv("S3_BUCKET_NAME")
    
    if not bucket:
        print("[ERROR] S3_BUCKET_NAME is not set. Cannot run backfill.")
        return

    con = get_duckdb_con()

    for date_str in target_dates:
        print(f"Starting Gold backfill for {date_str}...")
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            year = target_date.strftime("%Y")
            month = target_date.strftime("%m")
            day = target_date.strftime("%d")

            # Data stranded in Bronze/Silver -> Read from complete bronze layer
            bronze_path = f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
            gold_dir = f"s3://{bucket}/gold/year={year}/month={month}/day={day}"
            gold_path = f"{gold_dir}/regional_kpis.parquet"

            query = f"""
            COPY (
                WITH source as (
                    SELECT * FROM read_parquet('{bronze_path}', union_by_name=true)
                ),
                silver as (
                    SELECT
                        try_cast(extract_dt as timestamp) as extract_ts,
                        region_id,
                        region_name,
                        market_name,
                        commodity_group,
                        commodity_name,
                        try_cast(price as double) as price,
                        raw_date_text,
                        _dlt_load_id
                    FROM source
                    WHERE CAST(extract_dt AS DATE) = '{date_str}'
                ),
                clean_silver as (
                    SELECT * FROM silver
                    WHERE price <= 20000 AND price >= 0
                    AND not regexp_matches(CAST(region_name AS VARCHAR), '^[0-9.]+$')
                )
                SELECT 
                    region_name,
                    commodity_name as commodity,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    CASE 
                        WHEN AVG(price) > 0 THEN ((MAX(price) - MIN(price)) / AVG(price)) * 100 
                        ELSE 0 
                    END as price_volatility,
                    MAX(extract_ts) as latest_date,
                    0 as days_ago
                FROM clean_silver
                WHERE region_name IS NOT NULL AND commodity_name IS NOT NULL
                GROUP BY region_name, commodity_name
            ) TO '{gold_path}' (FORMAT 'parquet', OVERWRITE_OR_IGNORE true);
            """
            
            print(f"Executing aggregation and writing to {gold_path}...")
            con.execute(query)
            print(f"Successfully backfilled Gold layer for {date_str}.")

        except Exception as e:
            print(f"[ERROR] Failed to process {date_str}: {e}")

    con.close()
    print("Backfill process complete.")

if __name__ == "__main__":
    # Task 2: Hardcode target dates
    target_dates = ['2026-02-18', '2026-02-19']
    backfill_gold(target_dates)
