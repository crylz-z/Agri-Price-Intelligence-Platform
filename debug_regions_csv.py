import os
from src.dashboard.utils.data_engine import DataEngine

bucket = os.getenv("S3_BUCKET_NAME")
silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

con = DataEngine._get_connection()

query = f"""
SELECT region_name, COUNT(*) as cnt
FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
GROUP BY 1
ORDER BY 2 DESC
"""
df = con.sql(query).df()
df.to_csv("debug_out.csv", index=False)
print("Regions written to debug_out.csv")
