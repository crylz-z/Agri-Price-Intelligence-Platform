
import dlt
import os
from dotenv import load_dotenv
from src.etl.dlt_pipeline.agri_price_source import agri_price_source

load_dotenv()

def load():
    # Configure the pipeline
    # We use 'filesystem' destination. 
    # The bucket URL and credentials should be set in secrets.toml or env vars.
    # Env vars:
    # DESTINATION__FILESYSTEM__BUCKET_URL
    # DESTINATION__FILESYSTEM__CREDENTIALS__AWS_ACCESS_KEY_ID (if using keys)
    
    # For S3 path: s3://bucket_name/bronze/dlt_load/
    
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME env var is not set")
        
    destination_bucket_url = f"s3://{bucket_name}/bronze/dlt"
    
    pipeline = dlt.pipeline(
        pipeline_name="agri_price",
        destination=dlt.destinations.filesystem(destination_bucket_url),
        dataset_name="market_data"
    )

    # Run the pipeline
    load_info = pipeline.run(agri_price_source())
    print(load_info)

if __name__ == "__main__":
    load()
