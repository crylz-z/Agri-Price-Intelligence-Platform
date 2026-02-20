"""Quick test to check Silver layer schema in S3."""

import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

s3_bucket = os.getenv("S3_BUCKET_NAME")
aws_region = os.getenv("AWS_DEFAULT_REGION")
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")

print(f"S3 Bucket: {s3_bucket}")

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(f"SET s3_region='{aws_region}';")
con.execute(f"SET s3_access_key_id='{aws_key}';")
con.execute(f"SET s3_secret_access_key='{aws_secret}';")

silver_path = f"s3://{s3_bucket}/silver/year=*/month=*/day=*/*.parquet"

try:
    df = con.sql(
        f"SELECT * FROM read_parquet('{silver_path}', hive_partitioning=true) LIMIT 1"
    ).df()
    if df.empty:
        print("\n❌ Silver layer EXISTS but is EMPTY")
    else:
        print(f"\n✅ Silver layer has data")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Sample row:\n{df.head(1)}")
except Exception as e:
    print(f"\n❌ Silver layer query failed: {e}")
    print("\nTrying to check if any data exists...")
    try:
        bronze_path = f"s3://{s3_bucket}/bronze/year=*/month=*/day=*/*.csv"
        df_bronze = con.sql(
            f"SELECT * FROM read_csv_auto('{bronze_path}') LIMIT 1"
        ).df()
        if df_bronze.empty:
            print("❌ Bronze layer is also EMPTY - need to run extraction")
        else:
            print(f"✅ Bronze layer has data - need to run transformation")
            print(f"Bronze columns: {df_bronze.columns.tolist()}")
    except Exception as e2:
        print(f"❌ Bronze layer also failed: {e2}")
        print("\n🔴 NO DATA IN S3 - Run ETL pipeline first")

con.close()
