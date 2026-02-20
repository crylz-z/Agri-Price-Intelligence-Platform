"""
One-off script to migrate legacy CSV data (bronze/year=2026/...) to the new DLT Parquet architecture.
Run manually: python sandbox/backfill_csv_to_dlt.py
"""

import os
import boto3
import dlt
import pandas as pd
from dotenv import load_dotenv
from src.core.config import REGION_MAP

# Load env vars
load_dotenv()


def backfill_csvs():
    print("Starting backfill process...")
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "ap-southeast-2")

    # Source Path (Legacy CSVs)
    prefix = "bronze/year=2026/"

    print(f"Listing legacy CSVs from: s3://{bucket}/{prefix}")

    s3 = boto3.client("s3", region_name=region)
    keys = []

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".csv"):
                keys.append(obj["Key"])

    print(f"Found {len(keys)} CSV files.")

    all_records = []

    for key in keys:
        s3_path = f"s3://{bucket}/{key}"
        # print(f"Processing {key}...")
        try:
            df = pd.read_csv(
                s3_path,
                storage_options={
                    "key": os.getenv("AWS_ACCESS_KEY_ID"),
                    "secret": os.getenv("AWS_SECRET_ACCESS_KEY"),
                    "client_kwargs": {"region_name": region},
                },
            )

            for _, row in df.iterrows():
                try:
                    rid = str(row["region_id"])
                    # Handle potential float conversion for region_id if it was read as float
                    if rid.endswith(".0"):
                        rid = rid[:-2]

                    record = {
                        "extract_dt": row["extract_dt"],
                        "region_id": rid,
                        "region_name": REGION_MAP.get(rid, "Unknown"),
                        "market_name": row["market_name"],
                        "commodity_group": row["category"],
                        "commodity_name": row["commodity"],
                        "price": float(row["price"]),
                        "specifications": None,
                        "raw_date_text": row["extract_dt"],
                    }
                    all_records.append(record)
                except Exception:
                    # simplistic error handling
                    continue

        except Exception as file_err:
            print(f"Failed to read {key}: {file_err}")

    print(f"Transformed {len(all_records)} total records.")

    # Initialize DLT Pipeline (Same config as main pipeline)
    pipeline = dlt.pipeline(
        pipeline_name="agri_price",
        destination=dlt.destinations.filesystem(
            bucket_url=f"s3://{bucket}/bronze/dlt",
            credentials={
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "region_name": region,
            },
        ),
        dataset_name="market_data",
    )

    # Run Pipeline
    print("Loading to S3 (Parquet)...")
    load_info = pipeline.run(
        all_records, table_name="agri_price_resource", loader_file_format="parquet"
    )
    print(load_info)
    print("Backfill Complete.")


if __name__ == "__main__":
    backfill_csvs()
