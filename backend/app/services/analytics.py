from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.filters import genuine_airline_clause
from app.models.airport import Airport
from app.models.flight import Flight
from app.models.price_snapshot import PriceSnapshot
from app.models.route import Route

BASELINE_WINDOW_DAYS = 30


def _start_of_today() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min)


def _route_snapshot_query(db: Session, source: str, destination: str, *selectables):
    """Snapshot query joined through flight -> route -> origin/destination airports."""
    origin_airport = aliased(Airport)
    destination_airport = aliased(Airport)
    return (
        db.query(*selectables)
        .join(Flight, PriceSnapshot.flight_id == Flight.id)
        .join(Route, Flight.route_id == Route.id)
        .join(origin_airport, Route.origin_airport == origin_airport.id)
        .join(destination_airport, Route.destination_airport == destination_airport.id)
        .filter(
            origin_airport.iata_code == source.upper(),
            destination_airport.iata_code == destination.upper(),
            genuine_airline_clause(Flight.airline),
        )
    )


def _average_price(
    db: Session,
    source: str,
    destination: str,
    since: datetime,
    until: datetime | None = None,
) -> float | None:
    """Average snapshot price in a recorded_at window, or None when empty."""
    query = _route_snapshot_query(
        db, source, destination, func.avg(PriceSnapshot.price)
    ).filter(PriceSnapshot.recorded_at >= since)
    if until is not None:
        query = query.filter(PriceSnapshot.recorded_at < until)

    value = query.scalar()
    return float(value) if value is not None else None


def _classify_sources(sources: set[str]) -> str:
    if not sources:
        return "none"
    if sources == {"synthetic"}:
        return "synthetic"
    if sources == {"flightapi"}:
        return "flightapi"
    return "mixed"


def _route_data_source(
    db: Session,
    source: str,
    destination: str,
    since: datetime,
    until: datetime | None = None,
) -> str:
    query = _route_snapshot_query(db, source, destination, PriceSnapshot.source).filter(
        PriceSnapshot.recorded_at >= since
    )
    if until is not None:
        query = query.filter(PriceSnapshot.recorded_at < until)
    return _classify_sources({row[0] for row in query.distinct().all()})


def get_current_average(db: Session, source: str, destination: str) -> float | None:
    """Today's current/API fare, excluding synthetic historical rows."""
    current = (
        _route_snapshot_query(db, source, destination, func.avg(PriceSnapshot.price))
        .filter(
            PriceSnapshot.recorded_at >= _start_of_today(),
            PriceSnapshot.source != "synthetic",
        )
        .scalar()
    )
    if current is None:
        return None

    return float(current)


def get_route_baseline(
    db: Session,
    source: str,
    destination: str,
    days: int = BASELINE_WINDOW_DAYS,
) -> tuple[float | None, str | None]:
    """Average fare over the previous ``days`` days, excluding today.

    Returns ``(None, None)`` until stored historical snapshots exist. The
    baseline is never supplied by configuration or a hard-coded default.

    Returns ``(price, source_label)`` where ``source_label`` is
    ``history_30d`` for the prior-window average and ``history`` for fallbacks.
    """
    start_of_today = _start_of_today()
    window_start = start_of_today - timedelta(days=days)

    baseline = _average_price(
        db, source, destination, window_start, until=start_of_today
    )
    return (baseline, "history_30d") if baseline is not None else (None, None)


def calculate_price_index(
    db: Session,
    source: str,
    destination: str,
) -> dict[str, float] | None:
    """Compare today's fare against the route's 30-day historical baseline.

    Index = current average / 30-day baseline x 100, so 100 means fares sit
    exactly at their recent norm while 162.6 means they are 62.6% above it.
    """
    current_average_price = get_current_average(db, source, destination)
    if current_average_price is None:
        return None

    baseline_price, baseline_source = get_route_baseline(db, source, destination)
    if baseline_price is None or baseline_source is None:
        return None

    price_index = (current_average_price / baseline_price) * 100
    percentage_change = price_index - 100

    return {
        "current_average_price": current_average_price,
        "baseline_price": baseline_price,
        "baseline_source": baseline_source,
        "historical_source": _route_data_source(
            db, source, destination, _start_of_today() - timedelta(days=BASELINE_WINDOW_DAYS), _start_of_today()
        ),
        "price_index": price_index,
        "percentage_change": percentage_change,
    }


def _bucket_key(recorded_at: datetime, hourly: bool) -> datetime:
    """Floor a snapshot timestamp to its collection-time bucket start.

    Snapshots recorded during one collection run share (nearly) the same
    ``recorded_at`` — the flight API returns several flights/airlines per
    run.  Hourly floors keep runs in separate buckets for intraday views;
    daily floors aggregate per calendar day for longer ranges.  All
    timestamps are naive UTC in the database and treated as UTC here.
    """
    if hourly:
        return recorded_at.replace(minute=0, second=0, microsecond=0)
    return datetime.combine(recorded_at.date(), time.min)


def get_route_price_history(
    db: Session,
    source: str,
    destination: str,
    days: int = BASELINE_WINDOW_DAYS,
) -> dict:
    """Collection-time bucketed price history for the last ``days`` days.

    PriceSnapshot rows record one observed fare for one flight.  Several
    snapshots exist per collection run (one per airline/flight), so they
    must never be plotted as a single sequential line.  Instead, snapshots
    are grouped into collection-time buckets:

    - history spanning <= 1 day  -> hourly buckets (per collection hour)
    - history spanning > 1 day   -> daily buckets (average fare per day)

    Each bucket reports ``timestamp``, ``average_fare``, ``minimum_fare``,
    ``maximum_fare`` and ``snapshot_count``.  Buckets are returned sorted
    chronologically.  Duplicate timestamps are aggregated, never dropped,
    and no data is fabricated or smoothed.
    """
    window_start = _start_of_today() - timedelta(days=days - 1)
    rows = (
        _route_snapshot_query(
            db,
            source,
            destination,
            PriceSnapshot.recorded_at,
            PriceSnapshot.price,
            PriceSnapshot.source,
        )
        .filter(PriceSnapshot.recorded_at >= window_start)
        .order_by(PriceSnapshot.recorded_at.asc(), PriceSnapshot.id.asc())
        .all()
    )

    if not rows:
        return {"granularity": "hourly", "historical_source": "none", "history": []}

    distinct_dates = {recorded_at.date() for recorded_at, _price, _source in rows}
    hourly = len(distinct_dates) <= 1

    buckets: dict[datetime, dict[str, float]] = {}
    for recorded_at, price, _source in rows:
        key = _bucket_key(recorded_at, hourly)
        bucket = buckets.get(key)
        if bucket is None:
            buckets[key] = {
                "total": float(price),
                "minimum": float(price),
                "maximum": float(price),
                "count": 1,
            }
        else:
            bucket["total"] += float(price)
            bucket["minimum"] = min(bucket["minimum"], float(price))
            bucket["maximum"] = max(bucket["maximum"], float(price))
            bucket["count"] += 1

    history = []
    for key in sorted(buckets):  # chronological collection-time order
        bucket = buckets[key]
        history.append(
            {
                # Naive UTC in the DB -> tag as UTC for serialization so
                # FastAPI emits "...Z" and browsers render local time.
                "timestamp": key.replace(tzinfo=timezone.utc),
                "average_fare": round(bucket["total"] / bucket["count"], 2),
                "minimum_fare": round(bucket["minimum"], 2),
                "maximum_fare": round(bucket["maximum"], 2),
                "snapshot_count": bucket["count"],
            }
        )
    historical_source = _classify_sources(
        {
            source
            for recorded_at, _price, source in rows
        }
    )
    return {
        "granularity": "hourly" if hourly else "daily",
        "historical_source": historical_source,
        "history": history,
    }
