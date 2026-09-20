from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Route(Base):

    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)

    origin_airport = Column(
        Integer,
        ForeignKey("airports.id"),
        nullable=False,
        index=True,
    )

    destination_airport = Column(
        Integer,
        ForeignKey("airports.id"),
        nullable=False,
        index=True,
    )

    active = Column(Boolean, default=True, nullable=False)

    origin = relationship(
        "Airport",
        foreign_keys=[origin_airport],
        back_populates="departures",
    )

    destination = relationship(
        "Airport",
        foreign_keys=[destination_airport],
        back_populates="arrivals",
    )

    flights = relationship("Flight", back_populates="route")