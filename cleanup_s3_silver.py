"""List and clean up S3 Silver layer files."""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client('s3')
bucket = os.getenv("S3_BUCKET_NAME")

# List all Silver layer files
print(f"Listing S3 Silver layer files in {bucket}...")
response = s3.list_objects_v2(Bucket=bucket, Prefix="silver/")

if 'Contents' not in response:
    print("No files found in Silver layer")
    exit(0)

print(f"\nFound {len(response['Contents'])} files:")
for obj in response['Contents']:
    print(f"  - {obj['Key']} ({obj['Size']} bytes, {obj['LastModified']})")

print("\nDeleting OLD Silver files (not matching clean_prices.parquet pattern)...")
deleted_count = 0
for obj in response['Contents']:
    key = obj['Key']
    # Keep only clean_prices.parquet files, delete everything else
    if not key.endswith('clean_prices.parquet') and not key.endswith('/'):
        print(f"  Deleting: {key}")
        s3.delete_object(Bucket=bucket, Key=key)
        deleted_count += 1

print(f"\n✅ Deleted {deleted_count} old files")
print("Remaining files:")
response = s3.list_objects_v2(Bucket=bucket, Prefix="silver/")
if 'Contents' in response:
    for obj in response['Contents']:
        print(f"  - {obj['Key']}")
