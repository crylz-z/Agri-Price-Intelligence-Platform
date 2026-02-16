import os
import boto3
import sys
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_s3_bucket(bucket_name=None, region=None):
    """Create an S3 bucket in a specified region"""
    if bucket_name is None:
        bucket_name = os.getenv("S3_BUCKET_NAME")
    if region is None:
        region = os.getenv("AWS_DEFAULT_REGION")

        if not bucket_name:
        print("[ERROR] S3_BUCKET_NAME environment variable not set.")
        return False

    if not region:
        print("[ERROR] AWS_DEFAULT_REGION environment variable not set.")
        return False

    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"[INFO] Bucket '{bucket_name}' already exists.")
            return True
        except ClientError:
            pass # Bucket does not exist, proceed to create

        print(f"Creating bucket '{bucket_name}' in region '{region}'...")
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        
        print(f"[INFO] Successfully created bucket: {bucket_name} in {region}")
        return True

    except ClientError as e:
        print(f"[ERROR] Failed to create bucket: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    create_s3_bucket()
