import os
import json
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ── MLflow setup ──────────────────────────
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

def load_model(model_name: str = "stripe-fraud-detector", stage: str = "latest"):
    """Charge le modèle depuis MLflow registry."""
    model_uri = f"models:/{model_name}/{stage}"
    model     = mlflow.sklearn.load_model(model_uri)
    print(f"Model loaded : {model_uri}")
    return model

def predict_single(model, transaction: dict) -> dict:
    """
    Prédit le risque de fraude pour une transaction unique.

    transaction : dict avec les champs bruts
    retourne    : dict avec fraud_score, is_fraud, risk_level
    """
    from feature_engineering import build_features

    df  = pd.DataFrame([transaction])

    # Champs requis manquants → valeurs par défaut
    defaults = {
        "device_type":  "desktop",
        "ip_country":   "US",
        "status":       "success",
        "fraud_score":  0.0,
        "created_at":   pd.Timestamp.now(tz="UTC"),
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    features = build_features(df)
    feature_cols = [c for c in features.columns if c != "is_fraud"]
    X = features[feature_cols]

    proba      = model.predict_proba(X)[0][1]
    is_fraud   = bool(proba > 0.5)
    risk_level = (
        "HIGH"   if proba > 0.7 else
        "MEDIUM" if proba > 0.4 else
        "LOW"
    )

    result = {
        "transaction_id": transaction.get("id", "unknown"),
        "amount":         transaction.get("amount"),
        "currency":       transaction.get("currency_code"),
        "fraud_proba":    round(float(proba), 4),
        "is_fraud":       is_fraud,
        "risk_level":     risk_level,
    }
    return result

def predict_batch(model, transactions: list[dict]) -> pd.DataFrame:
    """Prédit le risque de fraude pour un batch de transactions."""
    from feature_engineering import build_features

    df = pd.DataFrame(transactions)

    defaults = {
        "device_type": "desktop",
        "ip_country":  "US",
        "status":      "success",
        "fraud_score": 0.0,
        "created_at":  pd.Timestamp.now(tz="UTC"),
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    features     = build_features(df)
    feature_cols = [c for c in features.columns if c != "is_fraud"]
    X            = features[feature_cols]

    probas     = model.predict_proba(X)[:, 1]
    df["fraud_proba"] = probas
    df["is_fraud"]    = probas > 0.5
    df["risk_level"]  = pd.cut(
        probas,
        bins=[-np.inf, 0.4, 0.7, np.inf],
        labels=["LOW", "MEDIUM", "HIGH"]
    )

    print(f"Batch prediction — {len(df)} transactions")
    print(f"  HIGH risk   : {(df['risk_level'] == 'HIGH').sum()}")
    print(f"  MEDIUM risk : {(df['risk_level'] == 'MEDIUM').sum()}")
    print(f"  LOW risk    : {(df['risk_level'] == 'LOW').sum()}")

    return df[["id", "amount", "currency_code", "fraud_proba", "is_fraud", "risk_level"]]

if __name__ == "__main__":
    model = load_model()

    # ── Test single prediction ─────────────
    print("\n── Single prediction ───────────────")
    test_transaction = {
        "id":           "test-001",
        "amount":       4800.00,
        "currency_code":"EUR",
        "device_type":  "mobile",
        "ip_country":   "NG",
        "status":       "success",
        "created_at":   pd.Timestamp.now(tz="UTC"),
        "fraud_score":  0.0,
    }
    result = predict_single(model, test_transaction)
    print(json.dumps(result, indent=2))

    # Test batch prediction 
    print("\n── Batch prediction ────────────────")
    batch = [
        {"id": "t1", "amount": 4999, "currency_code": "USD",
         "device_type": "mobile",  "ip_country": "NG", "status": "failed"},
        {"id": "t2", "amount": 50,   "currency_code": "EUR",
         "device_type": "desktop", "ip_country": "FR", "status": "success"},
        {"id": "t3", "amount": 3500, "currency_code": "GBP",
         "device_type": "tablet",  "ip_country": "US", "status": "success"},
        {"id": "t4", "amount": 12,   "currency_code": "EUR",
         "device_type": "desktop", "ip_country": "DE", "status": "success"},
        {"id": "t5", "amount": 4200, "currency_code": "USD",
         "device_type": "mobile",  "ip_country": "RU", "status": "failed"},
    ]
    df_results = predict_batch(model, batch)
    print(df_results.to_string(index=False))
