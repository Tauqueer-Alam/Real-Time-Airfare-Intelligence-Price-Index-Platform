import json
import os

from kafka import KafkaProducer

from app.events.price_events import AirfarePriceEvent

PRICE_EVENTS_TOPIC = "airfare-price-events"


def publish_price_event(event: AirfarePriceEvent) -> None:
    """Publish one validated price event to Kafka."""
    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
    )
    try:
        producer.send(
            PRICE_EVENTS_TOPIC,
            event.model_dump(mode="json"),
        ).get(timeout=10)
    finally:
        producer.flush()
        producer.close()
