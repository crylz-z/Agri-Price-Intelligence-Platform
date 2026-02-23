import os
from src.dashboard.utils.data_engine import DataEngine
from dotenv import load_dotenv

load_dotenv()
bucket = os.getenv("S3_BUCKET_NAME")
dlt_path = f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"

con = DataEngine._get_connection()

query = f"""
SELECT DISTINCT region_name, region_id
FROM read_parquet('{dlt_path}')
WHERE regexp_matches(CAST(region_name AS VARCHAR), '^[0-9.]+$') OR region_name IS NULL
LIMIT 50
"""
try:
    df = con.sql(query).df()
    print("Numeric or NULL region_name in DLT:")
    print(df)
except Exception as e:
    print("Error:", e)
