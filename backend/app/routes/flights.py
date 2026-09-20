from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.filters import genuine_airline_clause
from app.models.flight import Flight
from app.models.route import Route
from app.models.price_snapshot import PriceSnapshot
from app.models.user import User
from app.schemas.flight import (
    FlightCreate,
    FlightResponse,
    FlightUpdate,
    PriceSnapshotCreate,
    PriceSnapshotResponse,
)
from app.services.security import get_current_user

router = APIRouter(
    prefix="/api/flights",
    tags=["Flights"]
)


def _get_flight_or_404(flight_id: int, db: Session) -> Flight:
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


def _get_route_or_404(route_id: int, db: Session) -> Route:
    route = db.query(Route).filter(Route.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/")
def get_flights(db: Session = Depends(get_db)):
    """Return all flights, excluding non-genuine airlines (e.g. 'Duffel Airways')."""
    return (
        db.query(Flight)
        .filter(genuine_airline_clause(Flight.airline))
        .all()
    )


@router.get("/{flight_id}", response_model=FlightResponse)
def get_flight(flight_id: int, db: Session = Depends(get_db)):
    return _get_flight_or_404(flight_id, db)


@router.post("/", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
def create_flight(
    flight_data: FlightCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    _get_route_or_404(flight_data.route_id, db)

    new_flight = Flight(**flight_data.model_dump())
    db.add(new_flight)
    db.commit()
    db.refresh(new_flight)
    return new_flight


@router.put("/{flight_id}", response_model=FlightResponse)
def update_flight(
    flight_id: int,
    flight_data: FlightUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    flight = _get_flight_or_404(flight_id, db)

    update_data = flight_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No flight fields provided")

    if "route_id" in update_data:
        _get_route_or_404(update_data["route_id"], db)

    for field, value in update_data.items():
        setattr(flight, field, value)

    db.commit()
    db.refresh(flight)
    return flight


@router.delete("/{flight_id}")
def delete_flight(
    flight_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    flight = _get_flight_or_404(flight_id, db)

    db.delete(flight)
    db.commit()
    return {"message": "Flight deleted successfully"}


@router.post(
    "/{flight_id}/prices",
    response_model=PriceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_snapshot(
    flight_id: int,
    snapshot_data: PriceSnapshotCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    flight = _get_flight_or_404(flight_id, db)

    new_snapshot = PriceSnapshot(
        flight_id=flight.id,
        price=snapshot_data.price,
        currency=snapshot_data.currency.upper(),
        source=snapshot_data.source,
    )
    db.add(new_snapshot)
    db.commit()
    db.refresh(new_snapshot)
    return new_snapshot


@router.get("/{flight_id}/prices", response_model=list[PriceSnapshotResponse])
def get_price_history(flight_id: int, db: Session = Depends(get_db)):
    flight = _get_flight_or_404(flight_id, db)

    return (
        db.query(PriceSnapshot)
        .filter(PriceSnapshot.flight_id == flight.id)
        .order_by(PriceSnapshot.recorded_at.asc(), PriceSnapshot.id.asc())
        .all()
    )