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


def backfill_silver_gold(target_dates):
    """
    Backfills the Silver and Gold layers strictly following Medallion architecture.
    """
    load_dotenv()
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

            dlt_path = (
                f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
            )
            legacy_path = f"s3://{bucket}/bronze/year=2026/**/*.parquet"

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
                cases.append(f"WHEN region_id = '{rid}' THEN '{rname}'")
                if rid.startswith("0"):
                    cases.append(f"WHEN region_id = '{int(rid)}' THEN '{rname}'")
            case_sql = "CASE " + " ".join(cases) + " ELSE region_name END"

            silver_query = f"""
            COPY (
                WITH source as (
                    SELECT * FROM read_parquet(['{dlt_path}', '{legacy_path}'], union_by_name=true)
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
                AND not regexp_matches(CAST(region_name AS VARCHAR), '^[0-9.]+$')
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


if __name__ == "__main__":
    import sys

    # If dates are passed via command line (e.g., python script.py 2026-02-18 2026-02-19)
    if len(sys.argv) > 1:
        target_dates = sys.argv[1:]
    else:
        # Default to current system date
        target_dates = [datetime.now().strftime("%Y-%m-%d")]

    backfill_silver_gold(target_dates)
