"""Real-time airfare collector using the Duffel API.

Fetches live flight offers from the Duffel Flights API (https://duffel.com)
and publishes them as ``AirfarePriceEvent`` records. Works in two modes:

- **Kafka mode** (Docker): publishes events to Kafka for the price consumer.
- **Direct DB mode** (local): writes prices directly to PostgreSQL/SQLite.

The Duffel API uses versioned headers. This client targets ``v2`` which
supports the current Duffel endpoint structure.
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

DUFFEL_API_BASE = os.getenv("DUFFEL_API_BASE", "https://api.duffel.com")
DUFFEL_API_VERSION = os.getenv("DUFFEL_API_VERSION", "v2")

# Default routes to collect (source, destination) - several popular Indian routes
DEFAULT_ROUTES = [
    ("DEL", "BLR"),
    ("BOM", "DEL"),
    ("BLR", "BOM"),
    ("DEL", "BOM"),
    ("BLR", "DEL"),
]

# Cache the access token so we don't read env on every call
_ACCESS_TOKEN: str | None = None


def get_duffel_access_token() -> str:
    """Return the configured Duffel API access token."""
    global _ACCESS_TOKEN
    if _ACCESS_TOKEN is None:
        _ACCESS_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN", "").strip()
        if not _ACCESS_TOKEN:
            raise RuntimeError(
                "DUFFEL_ACCESS_TOKEN is not set. Add it to your .env file."
            )
    return _ACCESS_TOKEN


def _api_request(
    path: str,
    method: str = "GET",
    data: dict | None = None,
    timeout: int = 20,
) -> tuple[int, dict]:
    """Perform a JSON request against the Duffel API."""
    url = f"{DUFFEL_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_duffel_access_token()}",
        "Duffel-Version": DUFFEL_API_VERSION,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, method=method, headers=headers)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"errors": [{"message": body[:300]}]}
    except Exception as e:  # noqa: BLE001 - network errors vary
        return 0, {"errors": [{"message": str(e)}]}


def fetch_offers(
    source: str,
    destination: str,
    departure_date: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch real flight offers from Duffel for a given route.

    Returns a list of offer dictionaries from the Duffel API. An empty list
    is returned when the API is unreachable or returns no results.
    """
    if not departure_date:
        departure_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime(
            "%Y-%m-%d"
        )

    payload = {
        "data": {
            "slices": [
                {
                    "origin": source.upper(),
                    "destination": destination.upper(),
                    "departure_date": departure_date,
                }
            ],
            "passengers": [{"type": "adult"}],
            "cabin_class": "economy",
        }
    }

    status, data = _api_request("/air/offer_requests", method="POST", data=payload)
    if status not in (200, 201):
        errors = data.get("errors", [])
        message = errors[0].get("message", "unknown error") if errors else str(data)
        logger.warning("Duffel offer request failed: %s", message)
        return []

    return data.get("data", {}).get("offers", [])


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


def offers_to_price_events(
    offers: list[dict[str, Any]], source: str, destination: str
) -> list[AirfarePriceEvent]:
    """Convert raw Duffel offers into validated :class:`AirfarePriceEvent` records."""
    events: list[AirfarePriceEvent] = []
    for offer in offers:
        owner = offer.get("owner", {})
        airline = owner.get("name") or owner.get("iata_code") or "Unknown"
        airline_code = owner.get("iata_code") or ""

        # Skip non-genuine airlines (e.g. "Duffel Airways" from the test API)
        if not is_genuine_airline(airline):
            logger.info("Skipping non-genuine airline: %s", airline)
            continue

        slices = offer.get("slices", [])
        if not slices:
            continue

        # Use the first slice's schedule: departure from the first segment,
        # arrival from the last segment.
        flight_number = ""
        departure_time: datetime | None = None
        arrival_time: datetime | None = None
        for sl in slices:
            segments = sl.get("segments", [])
            if segments:
                seg = segments[0]
                flight_number = (
                    seg.get("marketing_carrier_flight_number")
                    or seg.get("operating_carrier_flight_number")
                    or ""
                )
                departure_time = _parse_iso_datetime(seg.get("departing_at"))
                arrival_time = _parse_iso_datetime(segments[-1].get("arriving_at"))
                break

        try:
            price = float(offer.get("total_amount", 0))
        except (ValueError, TypeError):
            logger.warning("Skipping offer with invalid price: %s", offer.get("id"))
            continue

        if price <= 0:
            continue

        # Convert USD to INR for consistency with the rest of the app
        currency = offer.get("total_currency", "USD")
        if currency == "USD":
            try:
                usd_inr_rate = float(os.getenv("DUFFEL_USD_INR_RATE", "83"))
            except ValueError:
                usd_inr_rate = 83.0
            if usd_inr_rate <= 0:
                usd_inr_rate = 83.0
            price = round(price * usd_inr_rate, 2)

        events.append(
            AirfarePriceEvent(
                airline=f"{airline} ({airline_code})".strip(),
                source=source.upper(),
                destination=destination.upper(),
                flight_number=flight_number or "N/A",
                price=price,
                currency="INR",
                data_source="duffel",
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
    """Fetch real airfare data from Duffel for the configured routes.

    Returns a list of collected events. When the Duffel API is unreachable,
    an empty list is returned instead of raising, so the scheduler can
    continue on the next tick.
    """
    if routes is None:
        routes = DEFAULT_ROUTES

    all_events: list[AirfarePriceEvent] = []
    for source, destination in routes:
        try:
            offers = fetch_offers(source, destination)
        except Exception:  # noqa: BLE001
            logger.exception("Duffel fetch failed for %s->%s", source, destination)
            continue

        limited_offers = offers[:max_offers_per_route]
        events = offers_to_price_events(limited_offers, source, destination)
        logger.info(
            "Collected %d real offers for %s -> %s",
            len(events),
            source,
            destination,
        )
        all_events.extend(events)

    return all_events


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    events = collect_once()
    print(f"Collected {len(events)} real airfare events")
    for event in events:
        print(event.model_dump_json())