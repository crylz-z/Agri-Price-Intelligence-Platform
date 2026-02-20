"""Delete all Silver and Gold files from S3, then re-run backfill."""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET_NAME")

print(f"Bucket: {bucket}")

for prefix in ["silver/", "gold/"]:
    print(f"\nDeleting {prefix} files...")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    deleted = 0
    for page in pages:
        if "Contents" not in page:
            continue

        objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
        if objects:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)

    print(f"  Deleted {deleted} objects from {prefix}")

print("\nDone. Now run: uv run python -m src.etl.transform.clean_data --backfill")
