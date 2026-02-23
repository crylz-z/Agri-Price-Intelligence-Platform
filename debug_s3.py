import os
import duckdb
import pandas as pd
from dotenv import load_dotenv


def debug_s3():
    load_dotenv()
    con = duckdb.connect(database=":memory:")
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
    bucket = os.getenv("S3_BUCKET_NAME")

    if not all([aws_key, aws_secret, aws_region, bucket]):
        print("Missing environment variables.")
        return

    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute(f"SET s3_region='{aws_region}';")
    con.execute(f"SET s3_access_key_id='{aws_key}';")
    con.execute(f"SET s3_secret_access_key='{aws_secret}';")

    bronze_path = (
        f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
    )

    print("--- 1. Checking Bronze Schema ---")
    try:
        schema = con.sql(
            f"DESCRIBE SELECT * FROM read_parquet('{bronze_path}') LIMIT 1"
        ).df()
        print(schema[["column_name", "column_type"]])
    except Exception as e:
        print(f"Error checking schema: {e}")

    print("\n--- 2. Checking for truly invalid extract_dt values ---")
    try:
        query = f"""
        SELECT
            extract_dt as raw_value,
            typeof(extract_dt) as raw_type,
            COUNT(*) as occurrences
        FROM read_parquet('{bronze_path}')
        WHERE TRY_CAST(extract_dt AS DATE) IS NULL
        AND extract_dt IS NOT NULL
        GROUP BY 1, 2
        LIMIT 20
        """
        invalid_dates = con.sql(query).df()
        if not invalid_dates.empty:
            print("Malformed records found:")
            print(invalid_dates)
        else:
            print("No malformed strings found.")
    except Exception as e:
        print(f"Error checking invalid dates: {e}")

    print("\n--- 3. Checking for out-of-range values in extract_dt ---")
    try:
        query = f"SELECT MIN(extract_dt) as min_val, MAX(extract_dt) as max_val FROM read_parquet('{bronze_path}')"
        bounds = con.sql(query).df()
        print(bounds)
    except Exception as e:
        print(f"Error checking bounds: {e}")

    print("\n--- 4. Finding source file for corrupted data ---")
    try:
        query = f"""
        SELECT DISTINCT "filename"
        FROM read_parquet('{bronze_path}', filename=true)
        WHERE extract_dt LIKE '>>>>>>>%' OR extract_dt LIKE '<<<<<<%'
        """
        bad_files = con.sql(query).df()
        if not bad_files.empty:
            print("Corrupted data found in these files:")
            for f in bad_files["filename"].tolist():
                print(f" - {f}")
        else:
            print("Could not locate specific file via quick LIKE check.")
    except Exception as e:
        print(f"Error finding bad files: {e}")

    con.close()


if __name__ == "__main__":
    debug_s3()
