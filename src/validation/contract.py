import pandera.pandas as pa
from pandera.typing import Series


class RawPriceSchema(pa.DataFrameModel):
    """
    Strict Data Contract for APIP Raw Price Data.
    enforces types and constraints before data enters the Silver Layer.
    """

    extract_dt: Series[str] = pa.Field(
        coerce=True
    )  # Check date format later or allow string for now
    region_id: Series[str] = pa.Field(coerce=True, nullable=False)
    market_name: Series[str] = pa.Field(coerce=True, nullable=False)
    category: Series[str] = pa.Field(coerce=True, nullable=False)
    commodity: Series[str] = pa.Field(coerce=True, nullable=False)
    price: Series[float] = pa.Field(
        ge=0, coerce=True, nullable=False
    )  # Price must be positive float

    class Config:
        strict = True  # Reject columns not defined in schema
        coerce = True  # Attempt to convert types (e.g. "10.50" -> 10.5)


if __name__ == '__main__':
    import sys
    import os
    import duckdb
    import pandas as pd
    from datetime import datetime
    from dotenv import load_dotenv
    from src.utils.logger import get_logger

    load_dotenv()
    logger = get_logger(__name__)

    # Date resolution: match clean_data.py logic
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        year, month, day = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
    except ValueError:
        logger.error(f"Invalid date format: {target_date}. Expected YYYY-MM-DD.")
        sys.exit(1)

    s3_bucket = os.getenv("S3_BUCKET_NAME")
    
    # Prioritize S3, fallback to local
    if s3_bucket:
        silver_path = f"s3://{s3_bucket}/silver/year={year}/month={month}/day={day}/clean_prices.parquet"
        
        # Configure DuckDB for S3 access
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_DEFAULT_REGION")
        
        if not all([aws_key, aws_secret, aws_region]):
            logger.error("Missing AWS credentials for S3 access")
            sys.exit(1)
        
        try:
            con = duckdb.connect(database=":memory:")
            con.execute("INSTALL httpfs;")
            con.execute("LOAD httpfs;")
            con.execute(f"SET s3_region='{aws_region}';")
            con.execute(f"SET s3_access_key_id='{aws_key}';")
            con.execute(f"SET s3_secret_access_key='{aws_secret}';")
            
            df = con.execute(f"SELECT * FROM read_parquet('{silver_path}')").df()
            con.close()
        except Exception as e:
            logger.error(f"Failed to read from S3: {e}. Attempting local fallback...")
            silver_path = f"data/clean/year={year}/month={month}/day={day}/market_prices.parquet"
            try:
                df = pd.read_parquet(silver_path)
            except Exception as local_e:
                logger.error(f"Failed to read local data: {local_e}")
                sys.exit(1)
    else:
        # Local fallback
        silver_path = f"data/clean/year={year}/month={month}/day={day}/market_prices.parquet"
        try:
            df = pd.read_parquet(silver_path)
        except Exception as e:
            logger.error(f"Failed to read local data: {e}")
            sys.exit(1)

    # Validate
    try:
        RawPriceSchema.validate(df, lazy=False)
        logger.info(f"Validation PASSED", date=target_date, rows=len(df), path=silver_path)
        print(f"✓ Validation PASSED for {target_date} ({len(df)} rows)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Validation FAILED", date=target_date, error=str(e))
        print(f"✗ Validation FAILED: {e}")
        sys.exit(1)
