import boto3
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_BUCKET_NAME")
if not bucket:
    print("S3_BUCKET_NAME not set")
    exit(1)

try:
    s3 = boto3.client('s3')
    today_prefix = "bronze/year=2026/month=02/day=16/"
    prefixes = ['bronze/', 'silver/', 'gold/', today_prefix]
    
    for prefix in prefixes:
        print(f"\n--- Checking '{prefix}' ---")
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if 'Contents' in resp:
            print(f"Found {len(resp['Contents'])} objects:")
            for obj in resp['Contents'][:3]:
                print(f" - {obj['Key']}")
        else:
            print(f"No objects found in '{prefix}'")
except Exception as e:
    print(f"Error listing S3: {e}")
