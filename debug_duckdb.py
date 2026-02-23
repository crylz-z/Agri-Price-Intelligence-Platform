import os
from src.dashboard.utils.data_engine import DataEngine

bucket = os.getenv("S3_BUCKET_NAME")
silver_path = f"s3://{bucket}/silver/year=*/month=*/day=*/*.parquet"

con = DataEngine._get_connection()

print("Checking files in S3...")
try:
    df1 = con.sql(
        f"SELECT COUNT(*) as file_count FROM read_parquet('{silver_path}')"
    ).df()
    print("Files exist:", df1)
except Exception as e:
    print("Error 1:", e)

query = f"""
SELECT extract_dt, price
FROM read_parquet('{silver_path}', union_by_name=true, hive_partitioning=1)
WHERE commodity = 'Rice - Regular Milled'
  AND region_name = 'REGION I (ILOCOS REGION)'
ORDER BY extract_dt DESC
LIMIT 5
"""
print("Checking specific query...")
try:
    df2 = con.sql(query).df()
    print("Data:", df2)
except Exception as e:
    print("Error 2:", e)
