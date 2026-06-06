import os
import duckdb
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Fraud by Country", page_icon="🌍", layout="wide")
st.title("🌍 Fraud by Country")
st.markdown("Analyse géographique du risque de fraude")

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
S3  = os.getenv("S3_BUCKET")

# Mapping ISO Alpha-2 → Alpha-3
ISO_MAP = {
    "US": "USA", "FR": "FRA", "DE": "DEU",
    "GB": "GBR", "JP": "JPN", "ES": "ESP",
    "IT": "ITA", "NL": "NLD", "RU": "RUS",
    "CN": "CHN", "BR": "BRA", "NG": "NGA",
}

df = con.execute(f"""
    SELECT
        ip_country,
        COUNT(*)                                            AS total,
        SUM(CASE WHEN fraud_score > 0.7 THEN 1 END)        AS nb_fraud,
        ROUND(
            100.0 * SUM(CASE WHEN fraud_score > 0.7 THEN 1 END) / COUNT(*),
        2)                                                  AS fraud_rate_pct,
        AVG(fraud_score)                                    AS avg_fraud_score
    FROM read_parquet('s3://{S3}/raw/transactions/full/*.parquet')
    WHERE ip_country IS NOT NULL
    GROUP BY ip_country
    ORDER BY fraud_rate_pct DESC
""").df()

# Ajoute colonne ISO Alpha-3
df["iso_alpha3"] = df["ip_country"].map(ISO_MAP)

# ── Table ─────────────────────────────────
st.subheader("Taux de fraude par pays")
st.dataframe(df[["ip_country", "total", "nb_fraud", "fraud_rate_pct", "avg_fraud_score"]],
             use_container_width=True)

# ── Bar chart ─────────────────────────────
fig1 = px.bar(
    df, x="ip_country", y="fraud_rate_pct",
    color="fraud_rate_pct",
    color_continuous_scale="Reds",
    title="Taux de fraude par pays (%)"
)
st.plotly_chart(fig1, use_container_width=True)

# ── Choropleth ────────────────────────────
fig2 = px.choropleth(
    df,
    locations="iso_alpha3",
    color="fraud_rate_pct",
    hover_name="ip_country",
    hover_data={"total": True, "nb_fraud": True, "fraud_rate_pct": True},
    color_continuous_scale="Reds",
    title="Carte mondiale du risque de fraude"
)
fig2.update_layout(
    geo=dict(showframe=False, showcoastlines=True, projection_type="equirectangular")
)
st.plotly_chart(fig2, use_container_width=True)
