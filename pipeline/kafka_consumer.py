import os
import json
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError
from pymongo import MongoClient
from datetime import datetime, timezone

load_dotenv()

# ── MongoDB ───────────────────────────────
mongo  = MongoClient(os.getenv("MONGODB_URI"))
db     = mongo["stripe_nosql"]

col_transactions = db["transactions"]
col_fraud        = db["fraud_alerts"]
col_logs         = db["logs"]

# ── Kafka consumer ────────────────────────
consumer = Consumer({
    "bootstrap.servers":  os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    "sasl.mechanisms":    "PLAIN",
    "security.protocol":  "SASL_SSL",
    "sasl.username":      os.getenv("KAFKA_API_KEY"),
    "sasl.password":      os.getenv("KAFKA_API_SECRET"),
    "group.id":           "stripe-mongo-consumer",
    "auto.offset.reset":  "earliest",
})

consumer.subscribe(["stripe.transactions", "stripe.fraud_alerts"])

# ── Indexes MongoDB ───────────────────────
col_transactions.create_index("id",          unique=True)
col_transactions.create_index("customer_id")
col_transactions.create_index("merchant_id")
col_transactions.create_index("created_at")
col_fraud.create_index("id",                 unique=True)
col_fraud.create_index("fraud_score")

# ── Validation ────────────────────────────
REQUIRED_KEYS = {"id", "customer_id", "merchant_id", "amount", "currency_code"}

def is_valid(event):
    return REQUIRED_KEYS.issubset(event.keys())

# ── Handlers ──────────────────────────────
def handle_transaction(event):
    col_transactions.update_one(
        {"id": event["id"]},
        {"$set": event},
        upsert=True
    )

def handle_fraud_alert(event):
    event["flagged_at"] = datetime.now(timezone.utc).isoformat()
    col_fraud.update_one(
        {"id": event["id"]},
        {"$set": event},
        upsert=True
    )
    col_logs.insert_one({
        "type":           "fraud_alert",
        "transaction_id": event["id"],
        "fraud_score":    event.get("fraud_score"),
        "amount":         event.get("amount"),
        "currency":       event.get("currency_code"),
        "logged_at":      datetime.now(timezone.utc).isoformat()
    })
    print(f"Fraud alert logged — score: {event.get('fraud_score')} "
          f"amount: {event.get('amount')} {event.get('currency_code')}")

# ── Boucle principale ─────────────────────
def main():
    print("Kafka consumer started — listening on stripe.transactions and stripe.fraud_alerts")
    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Kafka error: {msg.error()}")
                continue

            event = json.loads(msg.value().decode("utf-8"))

            if not is_valid(event):
                print(f"Skipped invalid message: {list(event.keys())}")
                continue

            topic = msg.topic()
            if topic == "stripe.transactions":
                handle_transaction(event)
            elif topic == "stripe.fraud_alerts":
                handle_fraud_alert(event)

    except KeyboardInterrupt:
        print("Consumer stopped.")
    finally:
        consumer.close()
        mongo.close()

if __name__ == "__main__":
    main()
