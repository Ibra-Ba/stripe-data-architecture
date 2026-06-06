import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

con = duckdb.connect()

con.execute(f"""
    SET s3_region            = '{os.getenv("AWS_REGION", "eu-west-1")}';
    SET s3_access_key_id     = '{os.getenv("AWS_ACCESS_KEY_ID")}';
    SET s3_secret_access_key = '{os.getenv("AWS_SECRET_ACCESS_KEY")}';
""")

# Transactions full
df_t = con.execute(f"""
    SELECT COUNT(*) AS nb_transactions
    FROM read_parquet('s3://{os.getenv("S3_BUCKET")}/raw/transactions/full/*.parquet')
""").df()

# Customers full
df_c = con.execute(f"""
    SELECT COUNT(*) AS nb_customers
    FROM read_parquet('s3://{os.getenv("S3_BUCKET")}/raw/customers/full/*.parquet')
""").df()

# Merchants full
df_m = con.execute(f"""
    SELECT COUNT(*) AS nb_merchants
    FROM read_parquet('s3://{os.getenv("S3_BUCKET")}/raw/merchants/full/*.parquet')
""").df()

print(df_t)
print(df_c)
print(df_m)

con.close()
