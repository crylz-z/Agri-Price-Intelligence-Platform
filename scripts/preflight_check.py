"""Pre-flight check: verify S3 bucket connectivity before pipeline run."""

import os
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def main() -> None:
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")

    if not bucket:
        print("FAIL: S3_BUCKET_NAME not set.")
        sys.exit(1)

    try:
        s3 = boto3.client("s3", region_name=region)
        s3.head_bucket(Bucket=bucket)
        print(f"OK: S3 bucket '{bucket}' reachable in {region}.")
    except NoCredentialsError:
        print("FAIL: AWS credentials not configured.")
        sys.exit(1)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"FAIL: S3 head_bucket returned {code}.")
        sys.exit(1)

if __name__ == "__main__":
    main()
