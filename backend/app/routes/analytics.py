from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.flight import PriceIndexResponse, RoutePriceHistoryResponse
from app.services.analytics import (
    BASELINE_WINDOW_DAYS,
    calculate_price_index,
    get_route_price_history,
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get("/price-index", response_model=PriceIndexResponse)
def get_price_index(
    source: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Compare today's average fare against the route's 30-day baseline."""
    normalized_source = source.strip().upper()
    normalized_destination = destination.strip().upper()
    price_index_data = calculate_price_index(
        db,
        normalized_source,
        normalized_destination,
    )

    if price_index_data is None:
        raise HTTPException(
            status_code=404,
            detail="No historical price data found for this route",
        )

    return {
        "source": normalized_source,
        "destination": normalized_destination,
        **price_index_data,
    }


@router.get("/price-history", response_model=RoutePriceHistoryResponse)
def get_price_history(
    source: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
    days: int = Query(BASELINE_WINDOW_DAYS, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Fares for the route, powering the dashboard trend chart.

    Individual snapshots (with timestamps) while history covers one day,
    daily averages once it spans multiple days.
    """
    normalized_source = source.strip().upper()
    normalized_destination = destination.strip().upper()
    history_data = get_route_price_history(
        db,
        normalized_source,
        normalized_destination,
        days,
    )

    return {
        "source": normalized_source,
        "destination": normalized_destination,
        "days": days,
        "granularity": history_data["granularity"],
        "historical_source": history_data["historical_source"],
        "history": history_data["history"],
    }
