import random
import psycopg2
from faker import Faker
from datetime import datetime, timedelta
from config import DB_URL, CURRENCIES, DEVICES, STATUSES, COUNTRIES

fake = Faker()

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
        is_fraud    = random.random() < 0.05       # 5% fraud rate
        fraud_score = round(random.uniform(0.75, 0.99), 4) if is_fraud \
                      else round(random.uniform(0.0, 0.35), 4)
        status      = "failed" if is_fraud and random.random() < 0.3 \
                      else random.choice(STATUSES)
        created_at  = fake.date_time_between(
                          start_date="-90d", end_date="now"
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
                round(random.uniform(1, 5000), 2),
                status,
                random.choice(DEVICES),
                random.choice(COUNTRIES),
                fraud_score,
                created_at
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"{n} transactions generated.")

if __name__ == "__main__":
    generate_transactions()
