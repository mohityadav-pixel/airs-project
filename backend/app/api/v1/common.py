"""Shared router helpers: entity resolution and freshness."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import logging

from app.core.errors import DataUnavailable, InvalidRequest
from app.core.logging_config import get_logger, log_event
from app.db.models import City, Station
from app.services import ingestion, repository

logger = get_logger("airs.api.refresh")

# How old the newest stored reading may be before we go back to the provider.
REFRESH_AFTER = timedelta(minutes=20)


def resolve_city(db: Session, slug: str | None) -> City:
    city = repository.get_city(db, slug) if slug else None
    if city is None and slug:
        raise InvalidRequest(f"Unknown city '{slug}'.")
    if city is None:
        cities = repository.list_cities(db)
        if not cities:
            raise DataUnavailable("No cities are configured. Run the database "
                                  "initialisation script.")
        city = cities[0]
    return city


def resolve_station(db: Session, city: City, station_id: int | None) -> Station:
    if station_id is not None:
        station = repository.get_station(db, station_id)
        if station is None:
            raise InvalidRequest("Unknown station.")
        return station
    stations = repository.city_stations(db, city.id)
    if not stations:
        raise DataUnavailable("This city has no active monitoring stations.")
    # Default to the station with the freshest reading.
    latest = repository.city_latest_readings(db, city.id)
    ranked = sorted(stations,
                    key=lambda s: (latest[s.id].observed_at if s.id in latest
                                    else datetime.min.replace(tzinfo=timezone.utc)),
                    reverse=True)
    return ranked[0]


def ensure_fresh(db: Session, city: City, station: Station) -> None:
    """Pull from upstream only when what we have is actually stale."""
    reading = repository.latest_air_quality(db, station.id)
    if reading is not None:
        age = datetime.now(timezone.utc) - reading.observed_at
        if age < REFRESH_AFTER:
            return
    try:
        ingestion.persist_snapshot(db, station, city)
    except Exception as exc:
        # Keep serving stored data — the payload marks it stale — but never
        # lose the reason. A silently failing live fetch looks exactly like
        # data loss from the browser.
        db.rollback()
        log_event(logger, logging.WARNING, "refresh_failed",
                  station=station.code, error=type(exc).__name__,
                  detail=str(getattr(exc, "detail", None) or exc)[:300])


# One page load may trigger at most this many upstream refreshes. Each costs an
# air-quality plus a weather round trip, so refreshing a ten-station city inline
# turned a dashboard load into six seconds of waiting. The hourly ingest script
# (scripts/ingest.py) is what keeps the whole network current; a page load only
# tops up the stalest few.
MAX_REFRESH_PER_REQUEST = 3


def ensure_city_fresh(db: Session, city: City) -> None:
    latest = repository.city_latest_readings(db, city.id)
    stations = repository.city_stations(db, city.id)
    now = datetime.now(timezone.utc)

    stale: list[tuple[datetime, Station]] = []
    for station in stations:
        reading = latest.get(station.id)
        if reading is None:
            stale.append((datetime.min.replace(tzinfo=timezone.utc), station))
        elif now - reading.observed_at >= REFRESH_AFTER:
            stale.append((reading.observed_at, station))

    stale.sort(key=lambda pair: pair[0])          # stalest first
    for _, station in stale[:MAX_REFRESH_PER_REQUEST]:
        try:
            ingestion.persist_snapshot(db, station, city)
        except Exception as exc:
            db.rollback()
            log_event(logger, logging.WARNING, "refresh_failed",
                      station=station.code, error=type(exc).__name__,
                      detail=str(getattr(exc, "detail", None) or exc)[:300])

    if len(stale) > MAX_REFRESH_PER_REQUEST:
        log_event(logger, logging.INFO, "refresh_deferred",
                  city=city.slug, refreshed=MAX_REFRESH_PER_REQUEST,
                  still_stale=len(stale) - MAX_REFRESH_PER_REQUEST)
