
import streamlit as st

st.set_page_config(
    page_title  = "Stripe Data Architecture",
    page_icon   = "💳",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Sidebar ───────────────────────────────
st.sidebar.title("💳 Stripe Analytics")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Jedha Bootcamp —  Bloc 2**
Architecture de données pour l'IA

**Stack**
- 🗄️ NeonDB (OLTP)
- 📨 Kafka (CDC streaming)
- 🍃 MongoDB Atlas (NoSQL)
- 🪣 AWS S3 (Data Lake)
- 🦆 DuckDB (OLAP)
- 🤖 scikit-learn + MLflow
""")
st.sidebar.markdown("---")
st.sidebar.markdown("Ibrahim BAH · 2026")

# ── Home ──────────────────────────────────
st.title("💳 Stripe Data Architecture Dashboard")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🚨 Fraud Detection
    Détection de fraude en temps réel
    via le modèle RandomForest tracké
    dans MLflow.

    **ROC-AUC : 0.9995**
    """)
    if st.button("→ Fraud Detection", use_container_width=True):
        st.switch_page("pages/01_fraud_detection.py")

with col2:
    st.markdown("""
    ### 📊 Revenue Analytics
    Métriques OLAP via DuckDB —
    revenus journaliers, performance
    marchands, analyse temporelle.

    **5 003 transactions**
    """)
    if st.button("→ Revenue Analytics", use_container_width=True):
        st.switch_page("pages/02_revenue_analytics.py")

with col3:
    st.markdown("""
    ### 🌍 Fraud by Country
    Analyse géographique du risque
    de fraude par pays via les
    agrégations pré-calculées.

    **8 pays analysés**
    """)
    if st.button("→ Fraud by Country", use_container_width=True):
        st.switch_page("pages/03_fraud_by_country.py")

st.markdown("---")

# ── Architecture overview ─────────────────
st.subheader("Architecture")
st.code("""
NeonDB (OLTP) ──► CDC Poller ──► Kafka ──► MongoDB Atlas (NoSQL)
      │
      ▼
GitHub Actions ──► AWS S3 (Parquet) ──► DuckDB (OLAP star schema)
      │
      ▼
scikit-learn + MLflow ──► Streamlit Dashboard (HuggingFace Spaces)
""", language=None)
