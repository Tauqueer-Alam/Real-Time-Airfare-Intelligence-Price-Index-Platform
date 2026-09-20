import random
from datetime import datetime, timezone

from app.events.price_events import AirfarePriceEvent
from app.services.kafka_producer import publish_price_event

SAMPLE_FLIGHTS = (
    ("IndiGo", "DEL", "BLR", "6E 234", 4200),
    ("Air India", "DEL", "BLR", "AI 506", 4800),
    ("Vistara", "BOM", "DEL", "UK 943", 5100),
    ("Akasa Air", "BLR", "BOM", "QP 1362", 3900),
)


def generate_mock_airfare_event() -> AirfarePriceEvent:
    """Generate development-only sample data without scraping any website."""
    airline, source, destination, flight_number, base_price = random.choice(SAMPLE_FLIGHTS)
    price = round(base_price * random.uniform(0.9, 1.15), 2)
    return AirfarePriceEvent(
        airline=airline,
        source=source,
        destination=destination,
        flight_number=flight_number,
        price=price,
        timestamp=datetime.now(timezone.utc),
    )


def collect_once() -> AirfarePriceEvent:
    """Publish one mock event; replace this function with a permitted data source later."""
    event = generate_mock_airfare_event()
    publish_price_event(event)
    return event


if __name__ == "__main__":
    print(collect_once().model_dump_json())
