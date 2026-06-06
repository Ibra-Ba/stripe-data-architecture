import os
from dotenv import load_dotenv
from confluent_kafka import Producer

load_dotenv()

conf = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    "sasl.mechanisms":   "PLAIN",
    "security.protocol": "SASL_SSL",
    "sasl.username":     os.getenv("KAFKA_API_KEY"),
    "sasl.password":     os.getenv("KAFKA_API_SECRET"),
}

producer = Producer(conf)

def delivery_report(err, msg):
    if err:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

producer.produce(
    "stripe.transactions",
    key="test",
    value='{"test": "ok"}',
    callback=delivery_report
)
producer.flush()