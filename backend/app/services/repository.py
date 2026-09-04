"""Read helpers. Keeps SQL out of the routers and the ML code."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (AirQualityReading, Alert, City, Prediction, Station,
                            TrafficReading, WeatherReading)


def get_city(db: Session, slug: str) -> City | None:
    return db.scalar(
        select(City).options(selectinload(City.stations)).where(City.slug == slug))


def list_cities(db: Session) -> list[City]:
    return list(db.scalars(select(City).order_by(City.name)))


def get_station(db: Session, station_id: int) -> Station | None:
    return db.get(Station, station_id)


def city_stations(db: Session, city_id: int) -> list[Station]:
    return list(db.scalars(select(Station)
                           .where(Station.city_id == city_id, Station.is_active.is_(True))
                           .order_by(Station.name)))


def latest_air_quality(db: Session, station_id: int) -> AirQualityReading | None:
    return db.scalar(select(AirQualityReading)
                     .where(AirQualityReading.station_id == station_id)
                     .order_by(AirQualityReading.observed_at.desc()).limit(1))


def latest_weather(db: Session, station_id: int) -> WeatherReading | None:
    return db.scalar(select(WeatherReading)
                     .where(WeatherReading.station_id == station_id)
                     .order_by(WeatherReading.observed_at.desc()).limit(1))


def latest_traffic(db: Session, station_id: int) -> TrafficReading | None:
    return db.scalar(select(TrafficReading)
                     .where(TrafficReading.station_id == station_id)
                     .order_by(TrafficReading.observed_at.desc()).limit(1))


def air_quality_series(db: Session, station_id: int, hours: int = 72,
                       end: datetime | None = None) -> list[AirQualityReading]:
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    return list(db.scalars(
        select(AirQualityReading)
        .where(AirQualityReading.station_id == station_id,
               AirQualityReading.observed_at >= start,
               AirQualityReading.observed_at <= end)
        .order_by(AirQualityReading.observed_at)))


def weather_series(db: Session, station_id: int, hours: int = 72,
                   end: datetime | None = None) -> list[WeatherReading]:
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    return list(db.scalars(
        select(WeatherReading)
        .where(WeatherReading.station_id == station_id,
               WeatherReading.observed_at >= start,
               WeatherReading.observed_at <= end)
        .order_by(WeatherReading.observed_at)))


def traffic_series(db: Session, station_id: int, hours: int = 72,
                   end: datetime | None = None) -> list[TrafficReading]:
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    return list(db.scalars(
        select(TrafficReading)
        .where(TrafficReading.station_id == station_id,
               TrafficReading.observed_at >= start,
               TrafficReading.observed_at <= end)
        .order_by(TrafficReading.observed_at)))


def range_series(db: Session, station_id: int, start: datetime,
                 end: datetime) -> list[AirQualityReading]:
    return list(db.scalars(
        select(AirQualityReading)
        .where(AirQualityReading.station_id == station_id,
               AirQualityReading.observed_at >= start,
               AirQualityReading.observed_at <= end)
        .order_by(AirQualityReading.observed_at)))


def city_latest_readings(db: Session, city_id: int) -> dict[int, AirQualityReading]:
    """Latest reading per station for a city, in one round trip."""
    sub = (select(AirQualityReading.station_id,
                  func.max(AirQualityReading.observed_at).label("max_at"))
           .join(Station, Station.id == AirQualityReading.station_id)
           .where(Station.city_id == city_id)
           .group_by(AirQualityReading.station_id).subquery())
    rows = db.scalars(
        select(AirQualityReading).join(
            sub, and_(AirQualityReading.station_id == sub.c.station_id,
                      AirQualityReading.observed_at == sub.c.max_at)))
    return {r.station_id: r for r in rows}


def city_latest_weather(db: Session, city_id: int) -> dict[int, WeatherReading]:
    sub = (select(WeatherReading.station_id,
                  func.max(WeatherReading.observed_at).label("max_at"))
           .join(Station, Station.id == WeatherReading.station_id)
           .where(Station.city_id == city_id)
           .group_by(WeatherReading.station_id).subquery())
    rows = db.scalars(
        select(WeatherReading).join(
            sub, and_(WeatherReading.station_id == sub.c.station_id,
                      WeatherReading.observed_at == sub.c.max_at)))
    return {r.station_id: r for r in rows}


def active_alerts(db: Session, city_id: int) -> list[Alert]:
    return list(db.scalars(
        select(Alert).where(Alert.city_id == city_id, Alert.is_active.is_(True))
        .order_by(Alert.raised_at.desc())))


def latest_predictions(db: Session, station_id: int,
                       issued_after: datetime | None = None) -> list[Prediction]:
    stmt: Select = select(Prediction).where(Prediction.station_id == station_id)
    if issued_after:
        stmt = stmt.where(Prediction.issued_at >= issued_after)
    return list(db.scalars(stmt.order_by(Prediction.target_at)))
