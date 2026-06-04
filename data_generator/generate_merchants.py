import random
import psycopg2
from faker import Faker
from config import DB_URL, COUNTRIES, CATEGORIES

fake = Faker()

def generate_merchants(n=50):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    for _ in range(n):
        cur.execute(
            """
            INSERT INTO merchants (name, country_code, category)
            VALUES (%s, %s, %s)
            """,
            (fake.company(), random.choice(COUNTRIES), random.choice(CATEGORIES))
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"{n} merchants generated.")

if __name__ == "__main__":
    generate_merchants()
