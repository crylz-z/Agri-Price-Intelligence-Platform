"""Test DuckDB S3 write capabilities."""
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
region = os.getenv("AWS_DEFAULT_REGION")
access_key = os.getenv("AWS_ACCESS_KEY_ID")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

print("Testing DuckDB S3 write capabilities...\n")

# Setup DuckDB with S3
con = duckdb.connect()
print("Step 1: Installing and loading httpfs extension...")
try:
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    print("✅ httpfs loaded\n")
except Exception as e:
    print(f"❌ Failed to load httpfs: {e}\n")
    exit(1)

print("Step 2: Configuring S3 credentials...")
try:
    con.execute(f"SET s3_region='{region}';")
    con.execute(f"SET s3_access_key_id='{access_key}';")
    con.execute(f"SET s3_secret_access_key='{secret_key}';")
    print("✅ S3 credentials configured\n")
except Exception as e:
    print(f"❌ Failed to configure S3: {e}\n")
    exit(1)

print("Step 3: Testing S3 read...")
try:
    # Try to read from existing Bronze data
    df = con.sql(f"SELECT * FROM read_csv_auto('s3://{bucket}/bronze/year=2026/month=02/day=17/*.csv', union_by_name=true) LIMIT 5").df()
    print(f"✅ Can read from S3 ({len(df)} rows)\n")
except Exception as e:
    print(f"❌ Cannot read from S3: {e}\n")
    exit(1)

print("Step 4: Testing DuckDB S3 write...")
test_s3_path = f"s3://{bucket}/test/duckdb_write_test.parquet"
try:
    con.execute(f"COPY (SELECT * FROM read_csv_auto('s3://{bucket}/bronze/year=2026/month=02/day=17/*.csv', union_by_name=true) LIMIT 10) TO '{test_s3_path}' (FORMAT PARQUET)")
    print(f"✅ Successfully wrote to S3 via DuckDB COPY\n")
except Exception as e:
    print(f"❌ DuckDB cannot write to S3: {e}\n")
    print("\nThis is the root cause of the transformation failure!")
    exit(1)

print("Step 5: Verifying written file...")
try:
    verify_df = con.sql(f"SELECT COUNT(*) as cnt FROM read_parquet('{test_s3_path}')").df()
    print(f"✅ Verified: {verify_df['cnt'].iloc[0]} rows in written file\n")
except Exception as e:
    print(f"❌ Cannot verify: {e}\n")

print("Step 6: Cleanup...")
import boto3
s3 = boto3.client('s3')
s3.delete_object(Bucket=bucket, Key="test/duckdb_write_test.parquet")
print("✅ Test file deleted\n")

con.close()

print("=" * 50)
print("✅ DUCKDB CAN WRITE TO S3")
print("=" * 50)
print("\nConclusion: DuckDB S3 writes are working.")
print("The transformation failure must be due to something else.")
