"""Pulls training rows out of the database and joins the three feeds."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (AirQualityReading, City, Station, TrafficReading,
                            WeatherReading)


def station_records(db: Session, station_id: int, *, days: int = 180,
                    end: datetime | None = None) -> list[dict]:
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    aq = db.scalars(select(AirQualityReading).where(
        AirQualityReading.station_id == station_id,
        AirQualityReading.observed_at >= start,
        AirQualityReading.observed_at <= end)).all()
    wx = {w.observed_at: w for w in db.scalars(select(WeatherReading).where(
        WeatherReading.station_id == station_id,
        WeatherReading.observed_at >= start,
        WeatherReading.observed_at <= end)).all()}
    tr = {t.observed_at: t for t in db.scalars(select(TrafficReading).where(
        TrafficReading.station_id == station_id,
        TrafficReading.observed_at >= start,
        TrafficReading.observed_at <= end)).all()}

    records: list[dict] = []
    for row in aq:
        w = wx.get(row.observed_at)
        t = tr.get(row.observed_at)
        records.append({
            "observed_at": row.observed_at,
            "aqi": row.aqi, "pm25": row.pm25, "pm10": row.pm10, "no2": row.no2,
            "so2": row.so2, "co": row.co, "o3": row.o3,
            "temperature_c": getattr(w, "temperature_c", None),
            "humidity_pct": getattr(w, "humidity_pct", None),
            "pressure_hpa": getattr(w, "pressure_hpa", None),
            "wind_speed_mps": getattr(w, "wind_speed_mps", None),
            "rain_1h_mm": getattr(w, "rain_1h_mm", None),
            "clouds_pct": getattr(w, "clouds_pct", None),
            "ventilation_index": getattr(w, "ventilation_index", None),
            "congestion_index": getattr(t, "congestion_index", None),
        })
    return records


def station_context(db: Session, station: Station) -> dict:
    city = db.get(City, station.city_id)
    # The model gets the city's own pollution level as a feature, so a station
    # in Shimla is not judged against Delhi's distribution.
    from app.db.seed_data import CITY_BASELINES
    baseline = CITY_BASELINES.get(city.slug if city else "", 50.0) * 1.6
    return {"zone": station.zone_type.value,
            "near_road": station.near_major_road,
            "near_industrial": station.near_industrial,
            "near_construction": station.near_construction,
            "city_baseline": baseline}
