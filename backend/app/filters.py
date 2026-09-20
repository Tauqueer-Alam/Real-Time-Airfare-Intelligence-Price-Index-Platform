"""Shared filtering helpers for excluding non-genuine airline data.

The FlightAPI.io API (especially with free or limited keys) can return
mock/placeholder offers whose carrier is named "Duffel Airways" — a
placeholder that is not a real airline.  These helpers let every layer
of the application (collector, search, analytics, frontend) consistently
exclude such non-genuine entries so that only real airlines appear in
results.
"""
from __future__ import annotations

import re

from sqlalchemy import and_
from sqlalchemy.sql.elements import ColumnElement

# Airline names that are not genuine carriers and should be filtered out.
# Matching is case-insensitive and substring-based so that variations like
# "Duffel Airways (DUFFEL)" are also caught.
NON_GENUINE_AIRLINES: tuple[str, ...] = (
    "duffel airways",
)

# Pre-compiled regex for efficient, case-insensitive substring matching.
_NON_GENUINE_PATTERN = re.compile(
    "|".join(re.escape(name) for name in NON_GENUINE_AIRLINES),
    re.IGNORECASE,
)


def is_genuine_airline(airline_name: str | None) -> bool:
    """Return ``True`` when *airline_name* refers to a genuine airline.

    ``None`` or empty values are treated as non-genuine so callers can use
    this as a simple truthiness + genuineness check.
    """
    if not airline_name:
        return False
    return _NON_GENUINE_PATTERN.search(airline_name) is None


def filter_genuine_airlines(airline_names: list[str]) -> list[str]:
    """Return only the airline names that refer to genuine carriers."""
    return [name for name in airline_names if is_genuine_airline(name)]


def genuine_airline_clause(airline_column) -> ColumnElement[bool]:
    """SQLAlchemy filter that keeps rows whose airline is a genuine carrier."""
    return and_(
        *[~airline_column.ilike(f"%{name}%") for name in NON_GENUINE_AIRLINES]
    )
