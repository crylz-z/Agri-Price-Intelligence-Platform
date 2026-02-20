import os
import duckdb

bucket = os.getenv("S3_BUCKET_NAME")
dlt_path = f"s3://{bucket}/bronze/dlt/market_data/agri_price_resource/**/*.parquet"
legacy_path = f"s3://{bucket}/bronze/year=2026/**/*.parquet"

silver_dir = f"s3://{bucket}/silver/year=2026/month=02/day=18"
silver_path = f"{silver_dir}/clean_prices_2026-02-18.parquet"

con = duckdb.connect()
con.execute(
    "INSTALL httpfs; LOAD httpfs; CREATE SECRET (TYPE s3, PROVIDER credential_chain);"
)

query = f"""
SELECT DISTINCT region_name, region_id
FROM read_parquet(['{dlt_path}', '{legacy_path}'], union_by_name=true)
LIMIT 10
"""
try:
    print(con.sql(query).df())
except Exception as e:
    print("Error:", e)
