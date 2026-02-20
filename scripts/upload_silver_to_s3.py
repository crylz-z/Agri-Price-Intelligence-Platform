"""Upload corrected local Silver layer to S3."""

import boto3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

s3_client = boto3.client("s3")
bucket = os.getenv("S3_BUCKET_NAME")

local_silver = Path("data/clean/year=2026/month=02/day=17/market_prices.parquet")

if not local_silver.exists():
    print(f"❌ Local Silver file not found: {local_silver}")
    exit(1)

s3_key = "silver/year=2026/month=02/day=17/clean_prices.parquet"

print(f"Uploading {local_silver} to s3://{bucket}/{s3_key}")

try:
    s3_client.upload_file(str(local_silver), bucket, s3_key)
    print(f"✅ Successfully uploaded Silver layer to S3")
    print(f"   Bucket: {bucket}")
    print(f"   Key: {s3_key}")
except Exception as e:
    print(f"❌ Upload failed: {e}")
    exit(1)
