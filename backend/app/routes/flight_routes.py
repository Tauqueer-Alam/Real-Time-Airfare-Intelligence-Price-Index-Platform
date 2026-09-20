"""Route (airport pair) management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.route import Route
from app.models.user import User
from app.schemas.flight import RouteCreate, RouteResponse
from app.services.airport_lookup import get_route_airport_pair
from app.services.security import get_current_user

router = APIRouter(
    prefix="/api/routes",
    tags=["Routes"],
)


@router.get("/", response_model=list[RouteResponse])
def get_routes(db: Session = Depends(get_db)):
    return db.query(Route).all()


@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    route_data: RouteCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a route between two airports, creating unknown airports on the fly.

    Idempotent: if the route already exists, the existing record is returned.
    """
    origin_code = route_data.origin.strip().upper()
    destination_code = route_data.destination.strip().upper()

    if origin_code == destination_code:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination airports must be different",
        )

    origin, destination = get_route_airport_pair(db, origin_code, destination_code)

    existing_route = (
        db.query(Route)
        .filter(
            Route.origin_airport == origin.id,
            Route.destination_airport == destination.id,
        )
        .first()
    )
    if existing_route is not None:
        return existing_route

    route = Route(
        origin_airport=origin.id,
        destination_airport=destination.id,
        active=route_data.active,
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route