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

# Tables exportées en full (référentiels — pas de filtre date)
FULL_TABLES = ["customers", "merchants"]

# Tables exportées par date (transactionnelles)
DATE_TABLES = ["transactions", "refunds"]

def export_full(table: str, date: datetime):
    """Export complet — référentiels."""
    year  = date.strftime("%Y")
    month = date.strftime("%m")
    day   = date.strftime("%d")

    print(f"Exporting full {table}...")
    df = pd.read_sql(f"SELECT * FROM {table}", get_engine())

    if df.empty:
        print(f"No data in {table} — skipping.")
        return

    local_path = f"/tmp/{table}_{year}{month}{day}.parquet"
    df.to_parquet(local_path, index=False)

    s3_key = f"raw/{table}/year={year}/month={month}/day={day}/{table}.parquet"
    get_s3().upload_file(local_path, os.getenv("S3_BUCKET"), s3_key)
    print(f"Uploaded {len(df)} rows → s3://{os.getenv('S3_BUCKET')}/{s3_key}")

def export_by_date(table: str, date: datetime):
    """Export filtré par date — tables transactionnelles."""
    year  = date.strftime("%Y")
    month = date.strftime("%m")
    day   = date.strftime("%d")

    print(f"Exporting {table} for {year}-{month}-{day}...")
    df = pd.read_sql(
        f"""
        SELECT * FROM {table}
        WHERE DATE(created_at) = '{date.strftime('%Y-%m-%d')}'
        """,
        get_engine()
    )

    if df.empty:
        print(f"No data for {table} on {date.strftime('%Y-%m-%d')} — skipping.")
        return

    local_path = f"/tmp/{table}_{year}{month}{day}.parquet"
    df.to_parquet(local_path, index=False)

    s3_key = f"raw/{table}/year={year}/month={month}/day={day}/{table}.parquet"
    get_s3().upload_file(local_path, os.getenv("S3_BUCKET"), s3_key)
    print(f"Uploaded {len(df)} rows → s3://{os.getenv('S3_BUCKET')}/{s3_key}")

def run():
    date = datetime.now(timezone.utc)

    for table in FULL_TABLES:
        export_full(table, date)

    for table in DATE_TABLES:
        export_by_date(table, date)

    print("Export complete.")

if __name__ == "__main__":
    run()