"""Check S3 Silver layer contents."""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client('s3')
bucket = os.getenv('S3_BUCKET_NAME')

print(f"Checking bucket: {bucket}")
print("\nSilver layer files:")
print("=" * 80)

resp = s3.list_objects_v2(Bucket=bucket, Prefix='silver/')

if 'Contents' in resp:
    for obj in resp['Contents']:
        print(f"{obj['Key']:<60} {obj['Size']:>10} bytes  {obj['LastModified']}")
else:
    print("No files found in silver/")
