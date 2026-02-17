import os
import sys
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
s3_bucket = os.getenv("S3_BUCKET_NAME")
if not s3_bucket:
    print("ERROR: S3_BUCKET_NAME environment variable not set")
    sys.exit(1)

try:
    s3_client = boto3.client("s3")
    s3_client.head_bucket(Bucket=s3_bucket)
    print(f"SUCCESS: S3 bucket '{s3_bucket}' is accessible")
    sys.exit(0)
except ClientError as e:
    error_code = e.response["Error"]["Code"]
    print(f"FAIL: S3 bucket '{s3_bucket}' check failed - {error_code}: {e}")
    sys.exit(1)
