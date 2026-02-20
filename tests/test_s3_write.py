"""Test S3 write permissions with boto3."""

import boto3
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
s3 = boto3.client("s3")

print(f"Testing S3 write permissions for bucket: {bucket}\n")

# Test 1: List objects
print("Test 1: List objects in bucket...")
try:
    response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
    print("✅ Can list objects\n")
except Exception as e:
    print(f"❌ Cannot list objects: {e}\n")
    exit(1)

# Test 2: Write a test file
print("Test 2: Write test file...")
test_key = "test/permissions_test.txt"
try:
    s3.put_object(Bucket=bucket, Key=test_key, Body=b"test data")
    print(f"✅ Can write files\n")
except Exception as e:
    print(f"❌ Cannot write files: {e}\n")
    exit(1)

# Test 3: Write a parquet file
print("Test 3: Write test parquet file...")
test_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
test_parquet_path = "test_local.parquet"
test_df.to_parquet(test_parquet_path)

test_parquet_key = "test/permissions_test.parquet"
try:
    s3.upload_file(test_parquet_path, bucket, test_parquet_key)
    print(f"✅ Can upload parquet files\n")
except Exception as e:
    print(f"❌ Cannot upload parquet: {e}\n")
    exit(1)

# Test 4: Delete test files
print("Test 4: Cleanup...")
try:
    s3.delete_object(Bucket=bucket, Key=test_key)
    s3.delete_object(Bucket=bucket, Key=test_parquet_key)
    os.remove(test_parquet_path)
    print("✅ Can delete files\n")
except Exception as e:
    print(f"❌ Cannot delete: {e}\n")

print("=" * 50)
print("✅ ALL S3 WRITE PERMISSIONS TESTS PASSED")
print("=" * 50)
print("\nConclusion: S3 credentials have proper write permissions.")
print("The issue might be with DuckDB's S3 write configuration.")
