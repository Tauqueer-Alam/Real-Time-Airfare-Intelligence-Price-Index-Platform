"""Scheduled airfare collection pipeline.

Runs inside the FastAPI lifespan and repeats every X hours:

    every X hours
        -> load active routes from the database
        -> call the live FlightAPI.io API
        -> receive offers
        -> publish Kafka events (or store directly when Kafka is off)
        -> price_snapshots rows accumulate

Control with environment variables:

- ``COLLECTION_INTERVAL_HOURS``: hours between collection runs (default 3).
- ``MOCK_COLLECTION_INTERVAL_SECONDS``: legacy seconds override, still honored.
- ``FLIGHTAPI_STORE_MODE``: ``kafka`` (default if Kafka is running) or ``direct``.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from app.collectors.flightapi_airfare_collector import (
    DEFAULT_ROUTES,
    collect_once as collect_flightapi,
)
from app.collectors.mock_airfare_collector import generate_mock_airfare_event
from app.events.price_events import AirfarePriceEvent
from app.services.price_consumer import process_price_event

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_INTERVAL_HOURS = 3.0
COLLECTION_INTERVAL_HOURS_ENV = "COLLECTION_INTERVAL_HOURS"
LEGACY_INTERVAL_SECONDS_ENV = "MOCK_COLLECTION_INTERVAL_SECONDS"


def get_collection_interval_seconds() -> float:
    """Resolve the collection cadence while keeping invalid settings non-fatal."""
    hours_value = os.getenv(COLLECTION_INTERVAL_HOURS_ENV)
    if hours_value:
        try:
            hours = float(hours_value)
        except ValueError:
            logger.warning(
                "Invalid %s; using default %sh",
                COLLECTION_INTERVAL_HOURS_ENV,
                DEFAULT_COLLECTION_INTERVAL_HOURS,
            )
        else:
            if hours <= 0:
                logger.warning(
                    "%s must be positive; using default %sh",
                    COLLECTION_INTERVAL_HOURS_ENV,
                    DEFAULT_COLLECTION_INTERVAL_HOURS,
                )
            else:
                return hours * 3600.0

    legacy_value = os.getenv(LEGACY_INTERVAL_SECONDS_ENV)
    if legacy_value:
        try:
            seconds = float(legacy_value)
        except ValueError:
            logger.warning("Invalid %s; ignoring it", LEGACY_INTERVAL_SECONDS_ENV)
        else:
            if seconds <= 0:
                logger.warning(
                    "%s must be positive; ignoring it", LEGACY_INTERVAL_SECONDS_ENV
                )
            else:
                return seconds

    return DEFAULT_COLLECTION_INTERVAL_HOURS * 3600.0


def get_active_route_pairs() -> list[tuple[str, str]]:
    """Load active routes from the database as (origin, destination) IATA pairs."""
    from sqlalchemy.orm import aliased

    from app.database.connection import SessionLocal
    from app.models.airport import Airport
    from app.models.route import Route

    origin_airport = aliased(Airport)
    destination_airport = aliased(Airport)
    db = SessionLocal()
    try:
        rows = (
            db.query(Route, origin_airport.iata_code, destination_airport.iata_code)
            .join(origin_airport, Route.origin_airport == origin_airport.id)
            .join(destination_airport, Route.destination_airport == destination_airport.id)
            .filter(Route.active.is_(True))
            .order_by(Route.id)
            .all()
        )
    finally:
        db.close()

    return [
        (origin_code, destination_code)
        for _route, origin_code, destination_code in rows
    ]


def _store_directly(events: list[AirfarePriceEvent]) -> None:
    """Write events directly to the database (no Kafka required)."""
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        for event in events:
            process_price_event(event, db)
        logger.info("Stored %d airfare events directly in DB", len(events))
    except Exception:
        db.rollback()
        logger.exception("Failed to store airfare events directly in DB")
    finally:
        db.close()


def _generate_mock_events_for_routes(routes: list[tuple[str, str]]) -> list[AirfarePriceEvent]:
    """Build a realistic mock event set for demo mode without external API access."""
    events: list[AirfarePriceEvent] = []
    for source, destination in routes:
        for index in range(4):
            event = generate_mock_airfare_event()
            event.source = source
            event.destination = destination
            event.airline = event.airline if index % 2 == 0 else "Air India"
            event.flight_number = f"{event.flight_number.split()[0]} {100 + index * 10}"
            event.price = round(float(event.price) * (1.0 + index * 0.04), 2)
            event.data_source = "mock"
            event.timestamp = datetime.now(timezone.utc)
            event.departure_time = event.timestamp + timedelta(hours=2 + index)
            event.arrival_time = event.departure_time + timedelta(hours=3)
            events.append(event)
    return events


async def run_scheduled_collection(
    stop_event: asyncio.Event,
    seed_task: asyncio.Task | None = None,
) -> None:
    """Collect real airfare prices from FlightAPI.io until FastAPI signals shutdown."""
    interval = get_collection_interval_seconds()
    store_mode = os.getenv("FLIGHTAPI_STORE_MODE", "kafka").lower()

    if store_mode == "direct":
        logger.warning("Running in direct DB store mode (no Kafka)")
    else:
        logger.info("Running in Kafka publish mode")
    logger.info(
        "Collecting airfare every %.1f hour(s)", interval / 3600.0
    )

    if seed_task is not None:
        await seed_task

    while not stop_event.is_set():
        try:
            routes = await asyncio.to_thread(get_active_route_pairs)
            if routes:
                logger.info("Collecting %d active route(s) from the database", len(routes))
            else:
                routes = DEFAULT_ROUTES
                logger.info("No active routes in DB yet; using built-in defaults")

            # Collect real flight offers from the FlightAPI.io API
            events = await asyncio.to_thread(collect_flightapi, routes)

            if not events:
                logger.warning("FlightAPI returned no data; using mock fallback for demo mode")
                events = _generate_mock_events_for_routes(routes)

            if store_mode == "direct" and events:
                await asyncio.to_thread(_store_directly, events)
            elif events:
                from app.services.kafka_producer import publish_price_event

                published = 0
                remaining_after_failure: list[AirfarePriceEvent] = []
                for index, event in enumerate(events):
                    try:
                        await asyncio.to_thread(publish_price_event, event)
                        published += 1
                    except Exception:
                        logger.warning(
                            "Failed to publish event to Kafka; falling back to direct DB"
                        )
                        remaining_after_failure = events[index:]
                        break

                if remaining_after_failure:
                    await asyncio.to_thread(_store_directly, remaining_after_failure)
                if published:
                    logger.info(
                        "Published %d airfare events to Kafka", published
                    )
        except Exception:
            # The API keeps serving even when Kafka/FlightAPI is temporarily unavailable.
            logger.exception("Scheduled airfare collection failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            pass
