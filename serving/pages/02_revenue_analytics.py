import os
import sys
import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Revenue Analytics", page_icon="📊", layout="wide")
st.title("📊 Revenue Analytics")
st.markdown("Métriques OLAP via DuckDB — star schema sur AWS S3")

@st.cache_resource
def get_con():
    con = duckdb.connect()
    con.execute(f"""
        SET s3_region            = '{os.getenv("AWS_REGION", "eu-west-1")}';
        SET s3_access_key_id     = '{os.getenv("AWS_ACCESS_KEY_ID")}';
        SET s3_secret_access_key = '{os.getenv("AWS_SECRET_ACCESS_KEY")}';
    """)
    return con

con = get_con()

S3 = os.getenv("S3_BUCKET")

# ── KPIs ──────────────────────────────────
df_kpi = con.execute(f"""
    SELECT
        COUNT(*)                                        AS total_transactions,
        SUM(amount)                                     AS total_revenue,
        AVG(amount)                                     AS avg_amount,
        SUM(CASE WHEN fraud_score > 0.7 THEN 1 END)    AS fraud_count
    FROM read_parquet('s3://{S3}/raw/transactions/full/*.parquet')
""").df()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total transactions", f"{int(df_kpi['total_transactions'][0]):,}")
col2.metric("Total revenue",      f"${df_kpi['total_revenue'][0]:,.0f}")
col3.metric("Avg transaction",    f"${df_kpi['avg_amount'][0]:,.0f}")
col4.metric("Fraud suspected",    f"{int(df_kpi['fraud_count'][0]):,}")

st.markdown("---")

# ── Revenue par devise ────────────────────
st.subheader("Revenue par devise")
df_currency = con.execute(f"""
    SELECT
        currency_code,
        COUNT(*)        AS nb_transactions,
        SUM(amount)     AS total_revenue
    FROM read_parquet('s3://{S3}/raw/transactions/full/*.parquet')
    WHERE status = 'success'
    GROUP BY currency_code
    ORDER BY total_revenue DESC
""").df()

fig1 = px.bar(
    df_currency, x="currency_code", y="total_revenue",
    color="currency_code", text="nb_transactions",
    title="Revenue par devise (transactions success)"
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# ── Top 10 marchands ──────────────────────
st.subheader("Top 10 marchands par volume")
df_merchants = con.execute(f"""
    SELECT
        m.name          AS merchant,
        m.category,
        COUNT(*)        AS nb_transactions,
        SUM(t.amount)   AS total_volume
    FROM read_parquet('s3://{S3}/raw/transactions/full/*.parquet') t
    JOIN read_parquet('s3://{S3}/raw/merchants/full/*.parquet') m
        ON t.merchant_id = m.id
    WHERE t.status = 'success'
    GROUP BY m.name, m.category
    ORDER BY total_volume DESC
    LIMIT 10
""").df()

fig2 = px.bar(
    df_merchants, x="total_volume", y="merchant",
    orientation="h", color="category",
    title="Top 10 marchands par volume"
)
st.plotly_chart(fig2, use_container_width=True)
