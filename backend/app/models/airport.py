from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Airport(Base):

    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)

    iata_code = Column(String(3), unique=True, nullable=False, index=True)

    name = Column(String, nullable=False)

    city = Column(String, nullable=False)

    country = Column(String, nullable=False)

    departures = relationship(
        "Route",
        foreign_keys="Route.origin_airport",
        back_populates="origin",
    )

    arrivals = relationship(
        "Route",
        foreign_keys="Route.destination_airport",
        back_populates="destination",
    )