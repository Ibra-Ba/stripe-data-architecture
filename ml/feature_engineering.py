import os
import duckdb
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

def load_features_from_duckdb() -> pd.DataFrame:
    """Charge les transactions depuis DuckDB/S3 et construit les features ML."""

    con = duckdb.connect()
    con.execute(f"""
        SET s3_region            = '{os.getenv("AWS_REGION", "eu-west-1")}';
        SET s3_access_key_id     = '{os.getenv("AWS_ACCESS_KEY_ID")}';
        SET s3_secret_access_key = '{os.getenv("AWS_SECRET_ACCESS_KEY")}';
    """)

    df = con.execute(f"""
        SELECT
            id, customer_id, merchant_id,
            amount, currency_code, status,
            payment_method_id, device_type,
            ip_country, fraud_score, created_at
        FROM read_parquet('s3://{os.getenv("S3_BUCKET")}/raw/transactions/full/*.parquet')
    """).df()

    con.close()
    print(f"Loaded {len(df)} transactions from DuckDB/S3.")
    return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les features pour le modèle de fraud detection."""

    # ── Encodage catégoriel ───────────────────
    df["device_mobile"]  = (df["device_type"] == "mobile").astype(int)
    df["device_desktop"] = (df["device_type"] == "desktop").astype(int)
    df["device_tablet"]  = (df["device_type"] == "tablet").astype(int)

    df["status_success"]  = (df["status"] == "success").astype(int)
    df["status_failed"]   = (df["status"] == "failed").astype(int)
    df["status_refunded"] = (df["status"] == "refunded").astype(int)

    # ── Features temporelles ──────────────────
    df["created_at"]  = pd.to_datetime(df["created_at"], utc=True)
    df["hour"]        = df["created_at"].dt.hour
    df["day_of_week"] = df["created_at"].dt.dayofweek
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
    df["is_night"]    = ((df["hour"] >= 22) | (df["hour"] <= 6)).astype(int)

    # ── Features montant ──────────────────────
    df["amount"]         = df["amount"].astype(float)
    df["amount_log"]     = np.log1p(df["amount"])
    df["is_high_amount"] = (df["amount"] > df["amount"].quantile(0.95)).astype(int)

    # ── Pays à risque ─────────────────────────
    high_risk_countries  = {"US", "RU", "CN", "BR", "NG"}
    df["high_risk_country"] = df["ip_country"].apply(
        lambda x: 1 if x in high_risk_countries else 0
    )

    # ── Target ────────────────────────────────
    df["is_fraud"] = (df["fraud_score"] > 0.7).astype(int)

    # ── Sélection features finales ────────────
    feature_cols = [
        "amount", "amount_log", "is_high_amount",
        "device_mobile", "device_desktop", "device_tablet",
        "status_success", "status_failed", "status_refunded",
        "hour", "day_of_week", "is_weekend", "is_night",
        "high_risk_country",
    ]

    df_features = df[feature_cols + ["is_fraud"]].dropna()
    print(f"Features built — {len(df_features)} samples, "
          f"{df_features['is_fraud'].sum()} fraud cases "
          f"({df_features['is_fraud'].mean()*100:.1f}%)")

    return df_features

if __name__ == "__main__":
    df_raw      = load_features_from_duckdb()
    df_features = build_features(df_raw)
    print(df_features.head())
