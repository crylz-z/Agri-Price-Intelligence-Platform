"""Delete ALL Silver layer files and upload only the new corrected one."""

import boto3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET_NAME")

# Delete ALL Silver layer files
print("Step 1: Deleting ALL Silver layer files...")
response = s3.list_objects_v2(Bucket=bucket, Prefix="silver/")
if "Contents" in response:
    for obj in response["Contents"]:
        print(f"  Deleting: {obj['Key']}")
        s3.delete_object(Bucket=bucket, Key=obj["Key"])
print("✅ All Silver files deleted\n")

# Upload the corrected local Silver file
local_silver = Path("data/clean/year=2026/month=02/day=17/market_prices.parquet")
s3_key = "silver/year=2026/month=02/day=17/clean_prices.parquet"

print(f"Step 2: Uploading corrected Silver layer...")
s3.upload_file(str(local_silver), bucket, s3_key)
print(f"✅ Uploaded to s3://{bucket}/{s3_key}\n")

# Verify
print("Step 3: Verifying upload...")
response = s3.list_objects_v2(Bucket=bucket, Prefix="silver/")
if "Contents" in response:
    print(f"Silver layer now has {len(response['Contents'])} file(s):")
    for obj in response["Contents"]:
        print(f"  - {obj['Key']} ({obj['Size']} bytes)")
