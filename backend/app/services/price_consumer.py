import json
import logging
import os

from kafka import KafkaConsumer
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.events.price_events import AirfarePriceEvent
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route
from app.services.airport_lookup import get_route_airport_pair
from app.services.kafka_producer import PRICE_EVENTS_TOPIC

logger = logging.getLogger(__name__)


def _as_naive(moment):
    """Strip timezone info so the value can be stored in a naive DateTime column."""
    if moment is not None and moment.tzinfo is not None:
        return moment.replace(tzinfo=None)
    return moment


def process_price_event(event: AirfarePriceEvent, db: Session) -> PriceSnapshot:
    """Resolve airport -> route -> flight, then save the price snapshot."""
    origin, destination = get_route_airport_pair(db, event.source, event.destination)

    route = (
        db.query(Route)
        .filter(
            Route.origin_airport == origin.id,
            Route.destination_airport == destination.id,
        )
        .first()
    )
    if route is None:
        route = Route(origin_airport=origin.id, destination_airport=destination.id)
        db.add(route)
        db.flush()

    departure_time = _as_naive(event.departure_time) or _as_naive(event.timestamp)

    flight = (
        db.query(Flight)
        .filter(
            Flight.route_id == route.id,
            func.lower(Flight.airline) == event.airline.lower(),
            func.lower(Flight.flight_number) == event.flight_number.lower(),
        )
        .first()
    )
    if flight is None:
        flight = Flight(
            route_id=route.id,
            airline=event.airline,
            flight_number=event.flight_number,
            departure_time=departure_time,
            arrival_time=_as_naive(event.arrival_time),
        )
        db.add(flight)
        db.flush()

    snapshot = PriceSnapshot(
        flight_id=flight.id,
        price=event.price,
        currency=event.currency.upper(),
        recorded_at=_as_naive(event.timestamp),
        source=event.data_source,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def consume_price_events() -> None:
    """Continuously validate Kafka messages and write valid events to PostgreSQL."""
    consumer = KafkaConsumer(
        PRICE_EVENTS_TOPIC,
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        group_id="airfare-price-consumer",
        enable_auto_commit=False,
    )

    try:
        for message in consumer:
            db = SessionLocal()
            try:
                payload = json.loads(message.value.decode("utf-8"))
                event = AirfarePriceEvent.model_validate(payload)
                process_price_event(event, db)
            except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
                logger.warning("Skipping invalid airfare price event: %s", error)
                db.rollback()
            except SQLAlchemyError:
                logger.exception("Unable to store airfare price event")
                db.rollback()
            finally:
                db.close()
                # Commit invalid messages too, so a malformed event cannot block the topic.
                consumer.commit()
    finally:
        consumer.close()


if __name__ == "__main__":
    consume_price_events()