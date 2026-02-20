import pandas as pd
import os
import s3fs
from dotenv import load_dotenv

load_dotenv()


def inspect_csv():
    bucket = os.getenv("S3_BUCKET_NAME")
    # Pick a random file from the dump or a known path
    # Using one from the previous list output
    file_key = "bronze/year=2026/month=02/day=18/prices_ncr_national_capital_region.csv"
    path = f"s3://{bucket}/{file_key}"

    print(f"Reading {path}...")
    try:
        df = pd.read_csv(
            path,
            storage_options={
                "key": os.getenv("AWS_ACCESS_KEY_ID"),
                "secret": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "client_kwargs": {
                    "region_name": os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
                },
            },
        )
        print(f"Writing to sandbox/csv_schema.txt...")
        with open("sandbox/csv_schema.txt", "w") as f:
            f.write(f"Columns: {df.columns.tolist()}\n")
            f.write(f"Sample: {df.head(1).to_dict(orient='records')}\n")
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    inspect_csv()
