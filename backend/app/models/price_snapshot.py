from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PriceSnapshot(Base):

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)

    price = Column(Float, nullable=False)

    currency = Column(String(3), default="INR", nullable=False)

    recorded_at = Column(DateTime, default=_utc_now_naive, nullable=False, index=True)

    source = Column(String, default="flightapi", nullable=False)

    flight = relationship("Flight", back_populates="price_snapshots")
