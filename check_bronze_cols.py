import duckdb
import os
from dotenv import load_dotenv

load_dotenv()
s3 = os.getenv("S3_BUCKET_NAME")
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"SET s3_region='{os.getenv('AWS_DEFAULT_REGION')}';")
con.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}';")

file1 = f"s3://{s3}/bronze/year=2026/month=02/day=17/prices_barmm_bangsamoro_autonomous_region_of_muslim_mindanao.csv"
file2 = f"s3://{s3}/bronze/year=2026/month=02/day=17/prices_region_i_ilocos_region.csv"

try:
    df1 = con.sql(f"SELECT * FROM read_csv_auto('{file1}', header=True) LIMIT 1").df()
    print(f"File 1 (BARMM) columns: {df1.columns.tolist()}")
except Exception as e:
    print(f"File 1 error: {e}")

try:
    df2 = con.sql(f"SELECT * FROM read_csv_auto('{file2}', header=True) LIMIT 1").df()
    print(f"File 2 (Region I) columns: {df2.columns.tolist()}")
except Exception as e:
    print(f"File 2 error: {e}")

con.close()
