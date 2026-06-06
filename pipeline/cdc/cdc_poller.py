import os
import json
import time
import psycopg2
import psycopg2.extras
from decimal import Decimal
from datetime import datetime, timedelta
from dotenv import load_dotenv
from confluent_kafka import Producer

load_dotenv()

# ── JSON serializer ───────────────────────
def json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# ── Kafka config ──────────────────────────
producer = Producer({
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    "sasl.mechanisms":   "PLAIN",
    "security.protocol": "SASL_SSL",
    "sasl.username":     os.getenv("KAFKA_API_KEY"),
    "sasl.password":     os.getenv("KAFKA_API_SECRET"),
})

def delivery_report(err, msg):
    if err:
        print(f"Delivery failed: {err}")
    else:
        print(f"Published to {msg.topic()} [{msg.partition()}] offset {msg.offset()}")

# ── NeonDB config ─────────────────────────
conn = psycopg2.connect(
    os.getenv("NEONDB_URL"),
    cursor_factory=psycopg2.extras.RealDictCursor
)

# ── State : dernière transaction vue ──────
last_seen = datetime.utcnow() - timedelta(minutes=5)

def poll_transactions():
    global last_seen
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            t.id, t.customer_id, t.merchant_id,
            t.amount, t.currency_code, t.status,
            t.fraud_score, t.device_type, t.ip_country,
            t.created_at
        FROM transactions t
        WHERE t.created_at > %s
        ORDER BY t.created_at ASC
        """,
        (last_seen,)
    )
    rows = cur.fetchall()
    cur.close()

    for row in rows:
        event = dict(row)
        event["id"]          = str(event["id"])
        event["customer_id"] = str(event["customer_id"])
        event["merchant_id"] = str(event["merchant_id"])

        topic = "stripe.fraud_alerts" \
                if (event["fraud_score"] or 0) > 0.7 \
                else "stripe.transactions"

        producer.produce(
            topic,
            key=event["id"],
            value=json.dumps(event, default=json_serial),
            callback=delivery_report
        )
        last_seen = row["created_at"]

    producer.flush()
    if rows:
        print(f"{len(rows)} events published — last seen: {last_seen}")

# ── Boucle principale ─────────────────────
if __name__ == "__main__":
    print("CDC poller started — polling every 10s")
    while True:
        poll_transactions()
        time.sleep(10)
