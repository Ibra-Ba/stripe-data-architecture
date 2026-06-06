import random
import psycopg2
import numpy as np
from faker import Faker
from datetime import datetime, timedelta, timezone
from config import DB_URL, CURRENCIES, DEVICES, STATUSES, COUNTRIES

fake = Faker()

HIGH_RISK_COUNTRIES = {"US", "RU", "CN", "BR", "NG"}

def compute_fraud_score(amount, device, ip_country, hour, status):
    """Fraud score déterministe basé sur les features réelles."""
    score = 0.0

    # Montant élevé = risque
    if amount > 4000:
        score += 0.35
    elif amount > 2000:
        score += 0.20
    elif amount > 1000:
        score += 0.10

    # Pays à risque
    if ip_country in HIGH_RISK_COUNTRIES:
        score += 0.20

    # Transaction nocturne (22h-6h)
    if hour >= 22 or hour <= 6:
        score += 0.15

    # Mobile = plus risqué
    if device == "mobile":
        score += 0.10

    # Transaction failed = signal
    if status == "failed":
        score += 0.15

    # Bruit léger
    score += random.uniform(-0.05, 0.05)

    return round(min(max(score, 0.0), 1.0), 4)

def get_ids(cur, table, column="id"):
    cur.execute(f"SELECT {column} FROM {table}")
    return [row[0] for row in cur.fetchall()]

def generate_transactions(n=5000):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    customer_ids = get_ids(cur, "customers")
    merchant_ids = get_ids(cur, "merchants")
    cur.execute("SELECT id FROM payment_methods")
    method_ids = [row[0] for row in cur.fetchall()]

    for _ in range(n):
        amount     = round(random.uniform(1, 5000), 2)
        device     = random.choice(DEVICES)
        ip_country = random.choice(COUNTRIES)
        status     = random.choice(STATUSES)
        created_at = fake.date_time_between(
            start_date="-90d", end_date="now"
        )
        hour        = created_at.hour
        fraud_score = compute_fraud_score(
            amount, device, ip_country, hour, status
        )

        cur.execute(
            """
            INSERT INTO transactions (
                customer_id, merchant_id, payment_method_id,
                currency_code, amount, status,
                device_type, ip_country, fraud_score, created_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                random.choice(customer_ids),
                random.choice(merchant_ids),
                random.choice(method_ids),
                random.choice(CURRENCIES),
                amount, status, device,
                ip_country, fraud_score, created_at
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"{n} transactions generated with deterministic fraud scores.")

if __name__ == "__main__":
    generate_transactions()
