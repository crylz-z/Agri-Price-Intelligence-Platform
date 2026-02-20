import boto3
import os
from dotenv import load_dotenv

load_dotenv()


def verify():
    bucket = os.getenv("S3_BUCKET_NAME")
    prefix = "bronze/dlt/"
    print(f"Checking {prefix} in {bucket}...")

    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))
    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        files = [
            obj["Key"]
            for obj in resp.get("Contents", [])
            if obj["Key"].endswith(".parquet")
        ]

        if files:
            print(f"Success! Found {len(files)} parquet files.")
            for f in files[:3]:
                print(f"FULL PATH: {f}")
        else:
            print("No parquet files found.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    verify()
