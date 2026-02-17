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

silver_path = f"s3://{s3}/silver/year=*/month=*/day=*/*.parquet"

df = con.sql(f"SELECT * FROM read_parquet('{silver_path}', hive_partitioning=true) LIMIT 1").df()
print(f"✅ S3 Silver layer columns ({len(df.columns)} total): {df.columns.tolist()}")
print(f"\nSample row:")
print(df.head(1).to_string(max_colwidth=20))

con.close()
