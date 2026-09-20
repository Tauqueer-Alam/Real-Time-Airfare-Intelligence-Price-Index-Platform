from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class AirfarePriceEvent(BaseModel):
    """The JSON contract exchanged between the collector and price consumer."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    airline: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=10)
    destination: str = Field(min_length=1, max_length=10)
    flight_number: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    data_source: str = Field(default="flightapi", min_length=1, max_length=50)
    timestamp: datetime
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
