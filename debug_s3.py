import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

def audit_bronze():
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

    bronze_path = f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
    
    with open("audit_result.txt", "w") as f:
        f.write("--- 1. DATE-BY-DATE CORRUPTION AUDIT ---\n")
        try:
            query = f"""
            SELECT 
                COALESCE(TRY_CAST(extract_dt AS DATE)::VARCHAR, 'CORRUPTED/NULL') as record_date,
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE TRY_CAST(extract_dt AS DATE) IS NULL AND extract_dt IS NOT NULL) as corruption_count
            FROM read_parquet('{bronze_path}')
            GROUP BY 1
            ORDER BY 1 DESC
            """
            audit = con.sql(query).df()
            f.write(audit.to_string(index=False))
            f.write("\n\n--- 2. CORRUPTION SAMPLES ---\n")
            query = f"""
            SELECT extract_dt as marker, COUNT(*) as count
            FROM read_parquet('{bronze_path}')
            WHERE TRY_CAST(extract_dt AS DATE) IS NULL AND extract_dt IS NOT NULL
            GROUP BY 1
            """
            samples = con.sql(query).df()
            f.write(samples.to_string(index=False))
        except Exception as e:
            f.write(f"Error checking audit: {e}\n")

    con.close()

if __name__ == "__main__":
    audit_bronze()
