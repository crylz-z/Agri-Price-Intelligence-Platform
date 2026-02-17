"""Simple check using boto3 to list Silver layer dates."""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client('s3')
bucket = os.getenv('S3_BUCKET_NAME')

print(f"Checking Silver layer in: {bucket}")

paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=bucket, Prefix='silver/')

dates_set = set()

for page in pages:
    if 'Contents' not in page:
        continue
        
    for obj in page['Contents']:
        key = obj['Key']
        if '/day=' in key:
            parts = key.split('/')
            for i, part in enumerate(parts):
                if part.startswith('day='):
                    day = part.split('=')[1]
                    month = parts[i-1].split('=')[1] if i > 0 else '??'
                    year = parts[i-2].split('=')[1] if i > 1 else '????'
                    dates_set.add(f"{year}-{month}-{day}")

dates = sorted(dates_set)

print(f"\nDates in Silver layer: {len(dates)}")
for date in dates:
    print(f"  - {date}")
