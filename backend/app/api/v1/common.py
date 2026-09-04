"""Shared router helpers: entity resolution and freshness."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import DataUnavailable, InvalidRequest
from app.db.models import City, Station
from app.services import ingestion, repository

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
    except Exception:
        db.rollback()   # keep serving what we have; the payload marks it stale


def ensure_city_fresh(db: Session, city: City) -> None:
    latest = repository.city_latest_readings(db, city.id)
    stations = repository.city_stations(db, city.id)
    now = datetime.now(timezone.utc)
    for station in stations:
        reading = latest.get(station.id)
        if reading is not None and now - reading.observed_at < REFRESH_AFTER:
            continue
        try:
            ingestion.persist_snapshot(db, station, city)
        except Exception:
            db.rollback()
