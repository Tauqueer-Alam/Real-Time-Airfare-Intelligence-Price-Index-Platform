from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AirportResponse(BaseModel):
    id: int
    iata_code: str
    name: str
    city: str
    country: str

    model_config = ConfigDict(from_attributes=True)


class RouteCreate(BaseModel):
    origin: str = Field(min_length=3, max_length=3, description="Origin IATA code")
    destination: str = Field(
        min_length=3, max_length=3, description="Destination IATA code"
    )
    active: bool = True


class RouteResponse(BaseModel):
    id: int
    active: bool
    origin: AirportResponse
    destination: AirportResponse

    model_config = ConfigDict(from_attributes=True)


class FlightCreate(BaseModel):
    route_id: int
    airline: str = Field(min_length=1)
    flight_number: str = Field(min_length=1)
    departure_time: datetime
    arrival_time: datetime | None = None


class FlightUpdate(BaseModel):
    route_id: int | None = None
    airline: str | None = Field(default=None, min_length=1)
    flight_number: str | None = Field(default=None, min_length=1)
    departure_time: datetime | None = None
    arrival_time: datetime | None = None


class FlightResponse(BaseModel):
    id: int
    route_id: int
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime | None

    model_config = ConfigDict(from_attributes=True)


class FlightSearchResult(BaseModel):
    id: int
    route_id: int
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime | None
    source: str
    destination: str
    price: float | None = None
    currency: str | None = None


class FlightSearchResponse(BaseModel):
    flights: list[FlightSearchResult]
    page: int
    limit: int
    total: int
    total_pages: int


class PriceSnapshotCreate(BaseModel):
    price: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    source: str = Field(default="manual", min_length=1, max_length=50)


class PriceSnapshotResponse(BaseModel):
    id: int
    flight_id: int
    price: float
    currency: str
    recorded_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)


class PriceIndexResponse(BaseModel):
    source: str
    destination: str
    current_average_price: float
    baseline_price: float
    baseline_source: str
    historical_source: str
    price_index: float
    percentage_change: float


class PriceHistoryPoint(BaseModel):
    """One collection-time bucket of the route price history.

    All PriceSnapshots recorded within the bucket (hourly for intraday
    history, daily for longer ranges) are aggregated: ``average_fare``,
    ``minimum_fare``, ``maximum_fare`` and ``snapshot_count``.
    """

    timestamp: datetime
    average_fare: float
    minimum_fare: float
    maximum_fare: float
    snapshot_count: int


class RoutePriceHistoryResponse(BaseModel):
    source: str
    destination: str
    days: int
    granularity: str = "hourly"
    historical_source: str = "none"
    history: list[PriceHistoryPoint]
