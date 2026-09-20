"""Real-time airfare collector using the FlightAPI.io API.

Fetches live flight offers from the FlightAPI.io Oneway Trip API
(https://www.flightapi.io) and publishes them as ``AirfarePriceEvent``
records. Works in two modes:

- **Kafka mode** (Docker): publishes events to Kafka for the price consumer.
- **Direct DB mode** (local): writes prices directly to PostgreSQL/SQLite.

The FlightAPI.io API uses a path-based key:
    GET https://api.flightapi.io/onewaytrip/{api_key}/{origin}/{destination}/{date}/{adults}/{children}/{infants}/{cabin_class}/{currency}
"""
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from app.events.price_events import AirfarePriceEvent
from app.filters import is_genuine_airline

logger = logging.getLogger(__name__)

FLIGHTAPI_API_BASE = os.getenv("FLIGHTAPI_API_BASE", "https://api.flightapi.io")

# Default routes to collect (source, destination) - several popular Indian routes
DEFAULT_ROUTES = [
    ("DEL", "BLR"),
    ("BOM", "DEL"),
    ("BLR", "BOM"),
    ("DEL", "BOM"),
    ("BLR", "DEL"),
]

# Cache the API key so we don't read env on every call
_API_KEY: str | None = None


def get_flightapi_key() -> str:
    """Return the configured FlightAPI.io API key."""
    global _API_KEY
    if _API_KEY is None:
        _API_KEY = os.getenv("FLIGHTAPI_API_KEY", "").strip()
        if not _API_KEY:
            raise RuntimeError(
                "FLIGHTAPI_API_KEY is not set. Add it to your .env file."
            )
    return _API_KEY


def _api_request(
    path: str,
    timeout: int = 30,
) -> tuple[int, dict]:
    """Perform a JSON GET request against the FlightAPI.io API."""
    url = f"{FLIGHTAPI_API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"message": body[:300]}
    except Exception as e:  # noqa: BLE001 - network errors vary
        return 0, {"message": str(e)}


def fetch_offers(
    source: str,
    destination: str,
    departure_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy",
    currency: str = "INR",
) -> list[dict[str, Any]]:
    """Fetch real flight offers from FlightAPI.io for a given route.

    Returns a list of itinerary dictionaries from the FlightAPI.io API.
    An empty list is returned when the API is unreachable or returns no results.
    """
    if not departure_date:
        departure_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime(
            "%Y-%m-%d"
        )

    api_key = get_flightapi_key()
    path = (
        f"/onewaytrip/{api_key}/{source.upper()}/{destination.upper()}/"
        f"{departure_date}/{adults}/{children}/{infants}/{cabin_class}/{currency}"
    )

    status, data = _api_request(path)
    if status != 200:
        message = data.get("message", str(data))
        logger.warning("FlightAPI request failed (status %s): %s", status, message)
        return []

    return data.get("itineraries", [])


def _parse_iso_datetime(value: Any) -> datetime | None:
    """Parse an ISO datetime string, assuming UTC when no offset is present."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _build_carrier_lookup(carriers: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Build a lookup from carrier ID to carrier info."""
    return {c["id"]: c for c in carriers}


def _build_segment_lookup(segments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a lookup from segment ID to segment info."""
    return {s["id"]: s for s in segments}


def _build_place_lookup(places: list[dict[str, Any]]) -> dict[int, str]:
    """Build a lookup from place ID to IATA code."""
    lookup: dict[int, str] = {}
    for place in places:
        code = place.get("display_code") or place.get("alt_id")
        if code:
            lookup[place["id"]] = code
    return lookup


def _resolve_carrier_name(
    carrier_id: int | None,
    carrier_lookup: dict[int, dict[str, Any]],
) -> tuple[str, str]:
    """Resolve a carrier ID to (name, iata_code)."""
    if carrier_id is None:
        return "Unknown", ""
    carrier = carrier_lookup.get(carrier_id, {})
    name = carrier.get("name", "Unknown")
    code = carrier.get("display_code", carrier.get("alt_id", ""))
    return name, code


def _resolve_flight_number(
    segment: dict[str, Any],
    carrier_lookup: dict[int, dict[str, Any]],
) -> str:
    """Build a flight number from the segment's marketing flight number and carrier code."""
    flight_number = segment.get("marketing_flight_number", "") or segment.get(
        "operating_flight_number", ""
    )
    carrier_id = segment.get("marketing_carrier_id")
    _, carrier_code = _resolve_carrier_name(carrier_id, carrier_lookup)
    if flight_number and carrier_code:
        return f"{carrier_code} {flight_number}"
    return flight_number or "N/A"


def _resolve_departure_arrival(
    segment_ids: list[str],
    segment_lookup: dict[str, dict[str, Any]],
) -> tuple[datetime | None, datetime | None]:
    """Get departure from first segment and arrival from last segment."""
    if not segment_ids:
        return None, None

    first_segment = segment_lookup.get(segment_ids[0], {})
    last_segment = segment_lookup.get(segment_ids[-1], {})

    departure = _parse_iso_datetime(first_segment.get("departure"))
    arrival = _parse_iso_datetime(last_segment.get("arrival"))
    return departure, arrival


def _resolve_airline(
    marketing_carrier_ids: list[int],
    operating_carrier_ids: list[int],
    carrier_lookup: dict[int, dict[str, Any]],
) -> tuple[str, str]:
    """Resolve the primary airline from marketing or operating carrier IDs."""
    for carrier_id in marketing_carrier_ids:
        name, code = _resolve_carrier_name(carrier_id, carrier_lookup)
        if name and name != "Unknown":
            return name, code

    for carrier_id in operating_carrier_ids:
        name, code = _resolve_carrier_name(carrier_id, carrier_lookup)
        if name and name != "Unknown":
            return name, code

    return "Unknown", ""


def itineraries_to_price_events(
    itineraries: list[dict[str, Any]],
    source: str,
    destination: str,
    carriers: list[dict[str, Any]] | None = None,
    segments: list[dict[str, Any]] | None = None,
    places: list[dict[str, Any]] | None = None,
) -> list[AirfarePriceEvent]:
    """Convert raw FlightAPI itineraries into validated AirfarePriceEvent records."""
    carrier_lookup = _build_carrier_lookup(carriers or [])
    segment_lookup = _build_segment_lookup(segments or [])
    # place_lookup is available if needed for origin/destination validation
    _build_place_lookup(places or [])

    events: list[AirfarePriceEvent] = []
    for itinerary in itineraries:
        pricing_options = itinerary.get("pricing_options", [])
        if not pricing_options:
            continue

        # Use the cheapest pricing option (first one is typically cheapest)
        pricing_option = pricing_options[0]
        price_info = pricing_option.get("price", {})
        try:
            price = float(price_info.get("amount", 0))
        except (ValueError, TypeError):
            logger.warning("Skipping itinerary with invalid price: %s", itinerary.get("id"))
            continue

        if price <= 0:
            continue

        # Get the first item which has segment_ids and carrier info
        items = pricing_option.get("items", [])
        if not items:
            continue

        item = items[0]
        segment_ids = item.get("segment_ids", [])
        marketing_carrier_ids = item.get("marketing_carrier_ids", [])

        # Also check the leg for carrier info
        leg_ids = itinerary.get("leg_ids", [])
        # Get carrier info from the leg if available
        legs = itinerary.get("_legs", [])  # legs are passed separately

        departure_time, arrival_time = _resolve_departure_arrival(
            segment_ids, segment_lookup
        )

        # Get flight number from first segment
        first_segment = segment_lookup.get(segment_ids[0], {}) if segment_ids else {}
        flight_number = _resolve_flight_number(first_segment, carrier_lookup)

        # Resolve airline
        airline_name, airline_code = _resolve_airline(
            marketing_carrier_ids,
            item.get("operating_carrier_ids", []),
            carrier_lookup,
        )

        # Skip non-genuine airlines
        if not is_genuine_airline(airline_name):
            logger.info("Skipping non-genuine airline: %s", airline_name)
            continue

        events.append(
            AirfarePriceEvent(
                airline=f"{airline_name} ({airline_code})".strip(),
                source=source.upper(),
                destination=destination.upper(),
                flight_number=flight_number,
                price=price,
                currency="INR",
                data_source="flightapi",
                timestamp=datetime.now(timezone.utc),
                departure_time=departure_time,
                arrival_time=arrival_time,
            )
        )

    return events


def collect_once(
    routes: list[tuple[str, str]] | None = None,
    max_offers_per_route: int = 5,
) -> list[AirfarePriceEvent]:
    """Fetch real airfare data from FlightAPI.io for the configured routes.

    Returns a list of collected events. When the API is unreachable,
    an empty list is returned instead of raising, so the scheduler can
    continue on the next tick.
    """
    if routes is None:
        routes = DEFAULT_ROUTES

    all_events: list[AirfarePriceEvent] = []
    for source, destination in routes:
        try:
            # Fetch itineraries
            api_key = get_flightapi_key()
            departure_date = (
                datetime.now(timezone.utc) + timedelta(days=7)
            ).strftime("%Y-%m-%d")
            path = (
                f"/onewaytrip/{api_key}/{source.upper()}/{destination.upper()}/"
                f"{departure_date}/1/0/0/economy/INR"
            )
            status, data = _api_request(path)
            if status != 200:
                message = data.get("message", str(data))
                logger.warning(
                    "FlightAPI request failed for %s->%s (status %s): %s",
                    source,
                    destination,
                    status,
                    message,
                )
                continue

            itineraries = data.get("itineraries", [])
            carriers = data.get("carriers", [])
            segments = data.get("segments", [])
            places = data.get("places", [])

            limited_itineraries = itineraries[:max_offers_per_route]
            events = itineraries_to_price_events(
                limited_itineraries,
                source,
                destination,
                carriers=carriers,
                segments=segments,
                places=places,
            )
            logger.info(
                "Collected %d real offers for %s -> %s",
                len(events),
                source,
                destination,
            )
            all_events.extend(events)

        except Exception:  # noqa: BLE001
            logger.exception(
                "FlightAPI fetch failed for %s->%s", source, destination
            )
            continue

    return all_events


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = collect_once()
    print(f"Collected {len(events)} real airfare events")
    for event in events:
        print(event.model_dump_json())
