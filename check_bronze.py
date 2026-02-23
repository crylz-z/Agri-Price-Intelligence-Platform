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
LIMIT 50
"""
try:
    df = con.sql(query).df()
    print("DLT Path output:")
    print(df)
except Exception as e:
    print("Error in DLT path query:", e)
