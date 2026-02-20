import dlt
import os
from dotenv import load_dotenv
from dlt.destinations import filesystem
from src.etl.dlt_pipeline.agri_price_source import agri_price_source

load_dotenv()


def load():
    """
    Configures and executes the dlt pipeline.
    Reads S3_BUCKET_NAME from the environment and writes extracted records
    to the Bronze layer at s3://<bucket>/bronze/dlt/.
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set.")

    s3_region = os.getenv(
        "AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
    )

    destination = filesystem(
        bucket_url=f"s3://{bucket_name}/bronze/dlt",
        credentials={"region_name": s3_region},
    )

    pipeline = dlt.pipeline(
        pipeline_name="agri_price",
        destination=destination,
        dataset_name="market_data",
    )

    # NOTE: Legacy .jsonl files in S3 (from before this fix) must be manually purged
    # to prevent schema conflicts. DLT will now strictly output Parquet.
    load_info = pipeline.run(agri_price_source(), loader_file_format="parquet")
    print(load_info)


if __name__ == "__main__":
    load()
