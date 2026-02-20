"""List all Bronze layer files in S3."""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client("s3")
bucket = os.getenv("S3_BUCKET_NAME")

print(f"Checking bucket: {bucket}")
print("\nBronze layer files:")
print("=" * 80)

resp = s3.list_objects_v2(Bucket=bucket, Prefix="bronze/")

if "Contents" in resp:
    files_by_date = {}
    for obj in resp["Contents"]:
        key = obj["Key"]
        # Extract date from path like bronze/year=2026/month=02/day=09/...
        if "/day=" in key:
            parts = key.split("/")
            for i, part in enumerate(parts):
                if part.startswith("day="):
                    day = part.split("=")[1]
                    month = (
                        parts[i - 1].split("=")[1]
                        if i > 0 and parts[i - 1].startswith("month=")
                        else "??"
                    )
                    year = (
                        parts[i - 2].split("=")[1]
                        if i > 1 and parts[i - 2].startswith("year=")
                        else "????"
                    )
                    date_str = f"{year}-{month}-{day}"
                    if date_str not in files_by_date:
                        files_by_date[date_str] = []
                    files_by_date[date_str].append(key)

    for date in sorted(files_by_date.keys()):
        print(f"\n{date}: {len(files_by_date[date])} files")
        for f in files_by_date[date][:3]:  # Show first 3
            print(f"  - {f}")
        if len(files_by_date[date]) > 3:
            print(f"  ... and {len(files_by_date[date]) - 3} more")

    print(f"\nTotal dates: {len(files_by_date)}")
else:
    print("No files found in bronze/")
