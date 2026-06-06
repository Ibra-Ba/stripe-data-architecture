import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'ml'))

import streamlit as st
import pandas as pd
import mlflow
import mlflow.sklearn
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Fraud Detection", page_icon="🚨", layout="wide")
st.title("🚨 Fraud Detection")
st.markdown("Prédiction temps réel via le modèle MLflow `stripe-fraud-detector`")

# ── Load model ────────────────────────────
@st.cache_resource
def load_model():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
    return mlflow.sklearn.load_model("models:/stripe-fraud-detector/latest")

model = load_model()

# ── Input form ────────────────────────────
st.subheader("Simuler une transaction")

col1, col2, col3 = st.columns(3)

with col1:
    amount      = st.number_input("Montant (€)", min_value=1.0, max_value=10000.0, value=500.0)
    currency    = st.selectbox("Devise", ["EUR", "USD", "GBP", "JPY", "CHF"])

with col2:
    device_type = st.selectbox("Device", ["desktop", "mobile", "tablet"])
    ip_country  = st.selectbox("Pays IP", ["FR", "DE", "GB", "US", "JP", "ES", "IT", "NL", "RU", "CN", "BR", "NG"])

with col3:
    status      = st.selectbox("Statut", ["success", "failed", "refunded"])
    hour        = st.slider("Heure de la transaction", 0, 23, 14)

if st.button("🔍 Analyser", use_container_width=True, type="primary"):
    from predict import predict_single

    transaction = {
        "id":           "live-test",
        "amount":       amount,
        "currency_code":currency,
        "device_type":  device_type,
        "ip_country":   ip_country,
        "status":       status,
        "created_at":   pd.Timestamp.now(tz="UTC").replace(hour=hour),
        "fraud_score":  0.0,
    }

    result = predict_single(model, transaction)

    st.markdown("---")
    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.metric("Fraud probability", f"{result['fraud_proba']*100:.1f}%")
    with col_r2:
        st.metric("Verdict", "🚨 FRAUD" if result["is_fraud"] else "✅ LEGIT")
    with col_r3:
        color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        st.metric("Risk level", f"{color[result['risk_level']]} {result['risk_level']}")

    if result["is_fraud"]:
        st.error(f"Transaction flagged as fraudulent — score {result['fraud_proba']:.4f}")
    else:
        st.success(f"Transaction looks legitimate — score {result['fraud_proba']:.4f}")
