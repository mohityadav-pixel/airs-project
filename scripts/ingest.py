"""Pull one live snapshot for every station and store it.

This is how AIRS builds real history: free air-quality APIs expose only the
current hour, so the platform has to accumulate its own time series. Run it
hourly.

    python -m scripts.ingest                  # every configured city
    python -m scripts.ingest --city delhi
    python -m scripts.ingest --loop --every 3600

macOS / Linux cron (hourly, on the hour):
    0 * * * * cd /path/to/airs-project && .venv/bin/python -m scripts.ingest
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.logging_config import configure_logging, get_logger, log_event  # noqa: E402
from app.db.init_db import init  # noqa: E402
from app.db.models import City  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.ingestion import ingest_city  # noqa: E402

logger = get_logger("airs.ingest")


def run_once(city_slug: str | None) -> None:
    with SessionLocal() as db:
        cities = list(db.scalars(
            select(City).where(City.slug == city_slug) if city_slug else select(City)))
        for city in cities:
            results = ingest_city(db, city)
            live = sum(1 for r in results if r.get("air_quality") == "live")
            failed = sum(1 for r in results if "error" in r)
            log_event(logger, 20, "city_ingested", city=city.slug,
                      stations=len(results), live=live, failed=failed)
            print(f"{city.slug}: {len(results)} stations, {live} live, "
                  f"{failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default=None)
    parser.add_argument("--loop", action="store_true",
                        help="Keep running instead of exiting after one pass.")
    parser.add_argument("--every", type=int, default=3600,
                        help="Seconds between passes when --loop is set.")
    args = parser.parse_args()

    configure_logging()
    init()
    if settings.airs_data_mode == "demo":
        print("AIRS_DATA_MODE=demo — this will store synthetic rows, labelled as "
              "demo. Set AIRS_DATA_MODE=live to collect real measurements.")

    if args.loop:
        while True:
            try:
                run_once(args.city)
            except Exception as exc:               # never let the loop die
                log_event(logger, 40, "ingest_pass_failed", error=type(exc).__name__)
            time.sleep(max(60, args.every))
    else:
        run_once(args.city)
