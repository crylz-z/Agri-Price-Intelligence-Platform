import boto3
import os
from dotenv import load_dotenv

load_dotenv()


def list_s3():
    bucket = os.getenv("S3_BUCKET_NAME")
    print(f"Listing bucket: {bucket}")
    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix="bronze/")
    print(f"Writing to s3_dump.txt...")
    with open("sandbox/s3_dump.txt", "w") as f:
        for page in pages:
            for obj in page.get("Contents", []):
                f.write(obj["Key"] + "\n")
    print("Done.")


if __name__ == "__main__":
    try:
        list_s3()
    except Exception as e:
        print(e)
