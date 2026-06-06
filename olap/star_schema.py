import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_KEY   = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SEC   = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REG   = os.getenv("AWS_REGION", "eu-west-1")

con = duckdb.connect("olap/stripe_olap.duckdb")

# ── S3 credentials ────────────────────────
con.execute(f"""
    SET s3_region            = '{AWS_REG}';
    SET s3_access_key_id     = '{AWS_KEY}';
    SET s3_secret_access_key = '{AWS_SEC}';
""")

# ── Chargement depuis S3 ──────────────────
print("Loading raw data from S3...")

con.execute(f"""
    CREATE OR REPLACE TABLE raw_transactions AS
    SELECT * FROM read_parquet('s3://{S3_BUCKET}/raw/transactions/full/*.parquet');
""")

con.execute(f"""
    CREATE OR REPLACE TABLE raw_customers AS
    SELECT * FROM read_parquet('s3://{S3_BUCKET}/raw/customers/full/*.parquet');
""")

con.execute(f"""
    CREATE OR REPLACE TABLE raw_merchants AS
    SELECT * FROM read_parquet('s3://{S3_BUCKET}/raw/merchants/full/*.parquet');
""")

print("Raw tables loaded.")

# ── Dimensions ────────────────────────────
print("Building dimensions...")

con.execute("""
    CREATE OR REPLACE TABLE dim_customer AS
    SELECT
        id              AS customer_key,
        email_hash,
        country_code,
        created_at      AS customer_since
    FROM raw_customers;
""")

con.execute("""
    CREATE OR REPLACE TABLE dim_merchant AS
    SELECT
        id              AS merchant_key,
        name            AS merchant_name,
        country_code    AS merchant_country,
        category        AS merchant_category
    FROM raw_merchants;
""")

con.execute("""
    CREATE OR REPLACE TABLE dim_time AS
    SELECT DISTINCT
        CAST(created_at AS DATE)            AS date_key,
        EXTRACT(YEAR  FROM created_at)      AS year,
        EXTRACT(MONTH FROM created_at)      AS month,
        EXTRACT(DAY   FROM created_at)      AS day,
        EXTRACT(DOW   FROM created_at)      AS day_of_week,
        EXTRACT(WEEK  FROM created_at)      AS week_of_year,
        EXTRACT(QUARTER FROM created_at)    AS quarter
    FROM raw_transactions;
""")

con.execute("""
    CREATE OR REPLACE TABLE dim_payment_method AS
    SELECT DISTINCT
        payment_method_id   AS payment_method_key,
        payment_method_id   AS method_name
    FROM raw_transactions;
""")

print("Dimensions built.")

# ── Fact table ────────────────────────────
print("Building fact_transactions...")

con.execute("""
    CREATE OR REPLACE TABLE fact_transactions AS
    SELECT
        t.id                                AS transaction_key,
        t.customer_id                       AS customer_key,
        t.merchant_id                       AS merchant_key,
        CAST(t.created_at AS DATE)          AS date_key,
        t.payment_method_id                 AS payment_method_key,
        t.currency_code,
        t.amount,
        t.status,
        t.device_type,
        t.ip_country,
        t.fraud_score,
        CASE WHEN t.fraud_score > 0.7
             THEN true ELSE false END       AS is_fraud_suspected,
        t.created_at
    FROM raw_transactions t;
""")

print("Fact table built.")

# ── Agrégations pré-calculées ─────────────
print("Building pre-aggregations...")

con.execute("""
    CREATE OR REPLACE TABLE agg_daily_revenue AS
    SELECT
        date_key,
        currency_code,
        COUNT(*)                                        AS nb_transactions,
        SUM(amount)                                     AS total_revenue,
        AVG(amount)                                     AS avg_amount,
        SUM(CASE WHEN status = 'success'  THEN 1 END)  AS nb_success,
        SUM(CASE WHEN status = 'failed'   THEN 1 END)  AS nb_failed,
        SUM(CASE WHEN is_fraud_suspected  THEN 1 END)  AS nb_fraud_suspected
    FROM fact_transactions
    GROUP BY date_key, currency_code
    ORDER BY date_key DESC;
""")

con.execute("""
    CREATE OR REPLACE TABLE agg_merchant_performance AS
    SELECT
        f.merchant_key,
        m.merchant_name,
        m.merchant_category,
        COUNT(*)            AS nb_transactions,
        SUM(f.amount)       AS total_volume,
        AVG(f.amount)       AS avg_transaction,
        SUM(CASE WHEN f.is_fraud_suspected THEN 1 END) AS nb_fraud
    FROM fact_transactions f
    JOIN dim_merchant m ON f.merchant_key = m.merchant_key
    GROUP BY f.merchant_key, m.merchant_name, m.merchant_category
    ORDER BY total_volume DESC;
""")

con.execute("""
    CREATE OR REPLACE TABLE agg_fraud_by_country AS
    SELECT
        ip_country,
        COUNT(*)                                            AS total,
        SUM(CASE WHEN is_fraud_suspected THEN 1 END)       AS nb_fraud,
        ROUND(
            100.0 * SUM(CASE WHEN is_fraud_suspected THEN 1 END) / COUNT(*),
        2)                                                  AS fraud_rate_pct,
        AVG(fraud_score)                                    AS avg_fraud_score
    FROM fact_transactions
    WHERE ip_country IS NOT NULL
    GROUP BY ip_country
    ORDER BY fraud_rate_pct DESC;
""")

print("Pre-aggregations built.")

# ── Validation ────────────────────────────
print("\n── Schema validation ──────────────────")
for table in [
    "dim_customer", "dim_merchant", "dim_time", "dim_payment_method",
    "fact_transactions",
    "agg_daily_revenue", "agg_merchant_performance", "agg_fraud_by_country"
]:
    count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table:<35} {count:>8} rows")

con.close()
print("\nStar schema complete.")
