import hashlib
import random
import psycopg2
from faker import Faker
from config import DB_URL, COUNTRIES

fake = Faker()

def generate_customers(n=500):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    for _ in range(n):
        email      = fake.email()
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        country    = random.choice(COUNTRIES)
        cur.execute(
            """
            INSERT INTO customers (email_hash, country_code)
            VALUES (%s, %s)
            ON CONFLICT (email_hash) DO NOTHING
            """,
            (email_hash, country)
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"{n} customers generated.")

if __name__ == "__main__":
    generate_customers()
