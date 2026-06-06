import os
import boto3
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

engine = None
s3     = None

def get_engine():
    global engine
    if engine is None:
        engine = create_engine(os.getenv("NEONDB_URL"))
    return engine

def get_s3():
    global s3
    if s3 is None:
        s3 = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION", "eu-west-1"),
        )
    return s3

def export_full(table: str):
    """Export complet de la table — historique."""
    print(f"Exporting full {table}...")

    df = pd.read_sql(f"SELECT * FROM {table}", get_engine())

    if df.empty:
        print(f"No data in {table} — skipping.")
        return

    local_path = f"/tmp/{table}_full.parquet"
    df.to_parquet(local_path, index=False)

    s3_key = f"raw/{table}/full/{table}.parquet"
    get_s3().upload_file(local_path, os.getenv("S3_BUCKET"), s3_key)
    print(f"Uploaded {len(df)} rows → s3://{os.getenv('S3_BUCKET')}/{s3_key}")

def run():
    for table in ["transactions", "customers", "merchants", "refunds"]:
        export_full(table)
    print("Full export complete.")

if __name__ == "__main__":
    run()
