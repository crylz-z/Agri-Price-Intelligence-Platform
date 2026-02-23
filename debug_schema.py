import os
from src.dashboard.utils.data_engine import DataEngine

bucket = os.getenv("S3_BUCKET_NAME")
silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

con = DataEngine._get_connection()

query = f"""
SELECT DISTINCT region_name, commodity
FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
LIMIT 20
"""
print("Checking distinct regions and commodities...")
df2 = con.sql(query).df()
print(df2)
