
import dlt
import os
from dotenv import load_dotenv
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

    destination_bucket_url = f"s3://{bucket_name}/bronze/dlt"

    pipeline = dlt.pipeline(
        pipeline_name="agri_price",
        destination=dlt.destinations.filesystem(destination_bucket_url),
        dataset_name="market_data",
    )

    load_info = pipeline.run(agri_price_source())
    print(load_info)


if __name__ == "__main__":
    load()
