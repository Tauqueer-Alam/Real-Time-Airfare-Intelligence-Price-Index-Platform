"""Generate idempotent synthetic historical airfare data for demos."""
from __future__ import annotations

import argparse
import logging

from app.database.connection import SessionLocal
from app.services.synthetic_history import (
    DEFAULT_DAYS,
    DEFAULT_SNAPSHOTS_PER_DAY,
    generate_synthetic_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic historical airfare snapshots."
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument(
        "--route",
        help="Existing route in SOURCE-DESTINATION form, for example DEL-BLR.",
    )
    parser.add_argument(
        "--snapshots-per-day",
        type=int,
        default=DEFAULT_SNAPSHOTS_PER_DAY,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = SessionLocal()
    try:
        inserted = generate_synthetic_history(
            db,
            days=args.days,
            route=args.route,
            snapshots_per_day=args.snapshots_per_day,
        )
    except ValueError as error:
        parser.error(str(error))
    finally:
        db.close()

    logging.info("Inserted %d synthetic historical snapshots", inserted)


if __name__ == "__main__":
    main()
