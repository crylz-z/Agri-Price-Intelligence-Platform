"""Pre-flight check: verify S3 bucket connectivity before pipeline run."""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def main() -> None:
    bucket_name = os.getenv("S3_BUCKET_NAME")
    configured_region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")

    if not bucket_name:
        print("[FAIL] S3_BUCKET_NAME not set.")
        sys.exit(1)

    print(f"[INFO] Checking bucket '{bucket_name}' (Configured Region: {configured_region})...")

    try:
        # Create client in the CONFIGURED region
        s3 = boto3.client("s3", region_name=configured_region)
        s3.head_bucket(Bucket=bucket_name)
        print(f"[OK] S3 bucket '{bucket_name}' reachable in '{configured_region}'.")
        sys.exit(0)

    except NoCredentialsError:
        print("[FAIL] AWS credentials not found or invalid.")
        sys.exit(1)

    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])

        if error_code == 404:
            print(f"[FAIL] Bucket '{bucket_name}' does not exist.")
            sys.exit(1)

        elif error_code in (301, 400):
            # 301/400 often means "Wrong Region". Let's find where it actually is.
            print(f"[WARN] Connection failed in '{configured_region}' (Error {error_code}). Diagnosing actual region...")
            try:
                # Use a client without a specific region to ask for location
                s3_global = boto3.client("s3")
                response = s3_global.get_bucket_location(Bucket=bucket_name)
                actual_region = response["LocationConstraint"] or "us-east-1"
                
                print(f"[FAIL] Region Mismatch! Bucket is in '{actual_region}', but config uses '{configured_region}'.")
                print(f"       Action: Update AWS_DEFAULT_REGION in .env to '{actual_region}'.")
                sys.exit(1)
            except Exception as diag_e:
                print(f"[FAIL] Could not determine actual bucket region: {diag_e}")
                sys.exit(1)
        
        else:
            print(f"[FAIL] S3 Error: {error_code} - {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
