from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Flight(Base):

    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)

    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)

    airline = Column(String, nullable=False)

    flight_number = Column(String, nullable=False)

    departure_time = Column(DateTime, nullable=False)

    arrival_time = Column(DateTime, nullable=True)

    route = relationship("Route", back_populates="flights")

    price_snapshots = relationship(
        "PriceSnapshot",
        back_populates="flight",
        cascade="all, delete-orphan",
    )