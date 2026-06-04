import psycopg2
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_generator'))

from dotenv import load_dotenv
from config import DB_URL

load_dotenv()

def seed_reference_tables(cur):
    currencies = [
        ("USD", "US Dollar"), ("EUR", "Euro"), ("GBP", "British Pound"),
        ("JPY", "Japanese Yen"), ("CHF", "Swiss Franc")
    ]
    cur.executemany(
        "INSERT INTO currencies (code, name) VALUES (%s,%s) ON CONFLICT DO NOTHING",
        currencies
    )

    countries = [
        ("US","United States","Americas"), ("FR","France","Europe"),
        ("DE","Germany","Europe"),         ("GB","United Kingdom","Europe"),
        ("JP","Japan","Asia"),             ("ES","Spain","Europe"),
        ("IT","Italy","Europe"),           ("NL","Netherlands","Europe")
    ]
    cur.executemany(
        "INSERT INTO countries (code, name, region) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
        countries
    )

    methods = [("card",), ("bank_transfer",), ("wallet",)]
    cur.executemany(
        "INSERT INTO payment_methods (name) VALUES (%s) ON CONFLICT DO NOTHING",
        methods
    )

    print("Reference tables seeded.")

def run():
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    print("Seeding reference tables...")
    seed_reference_tables(cur)
    conn.commit()

    print("Generating customers...")
    from generate_customers import generate_customers
    generate_customers(500)

    print("Generating merchants...")
    from generate_merchants import generate_merchants
    generate_merchants(50)

    print("Generating transactions...")
    from generate_transactions import generate_transactions
    generate_transactions(5000)

    cur.close()
    conn.close()
    print("Seed complete.")

if __name__ == "__main__":
    run()
