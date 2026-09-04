"""Ingestion orchestration: providers -> validation -> normalised rows -> DB.

Mode resolution (``AIRS_DATA_MODE``)
------------------------------------
``live``  fetch upstream; on failure serve last-known-good from cache and mark
          the response ``stale``; never substitute synthetic values.
``demo``  never call upstream; every row is synthetic and stamped ``demo``.
``auto``  live -> cache -> synthetic, and the response always states which of
          the three it actually used.

The API returns that resolution to the browser so the UI can render an honest
LIVE / CACHED / DEMO badge. There is no code path where synthetic data is
labelled live.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import settings
from app.core.errors import ProviderNotConfigured, ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.db.models import (AirQualityReading, City, Provenance, Station,
                            TrafficReading, WeatherReading)
from app.services import validation
from app.services.providers.demo import (synth_air_quality, synth_traffic,
                                          synth_weather)
from app.services.providers.openweather import OpenWeatherProvider, ventilation_index
from app.services.providers.waqi import WaqiProvider

logger = get_logger("airs.ingestion")

AQ_TTL_SECONDS = 600      # WAQI publishes hourly; 10 min is polite and fresh
WEATHER_TTL_SECONDS = 600

aq_provider = WaqiProvider()
weather_provider = OpenWeatherProvider()


class Resolution:
    LIVE = "live"
    CACHED = "cached"
    DEMO = "demo"


def _hours_local(ts: datetime) -> int:
    return ts.astimezone(timezone(timedelta(hours=5, minutes=30))).hour


# ─────────────────────────── air quality ──────────────────────────────

def fetch_air_quality(station: Station, city: City) -> tuple[object, str]:
    """Returns (observation, resolution)."""
    key = f"aq:{station.id}"
    mode = settings.airs_data_mode

    if mode != "demo":
        cached = cache.get(key)
        if cached is not None:
            return cached, Resolution.LIVE
        try:
            obs = aq_provider.fetch(station.latitude, station.longitude)
            obs = validation.validate_air_quality(obs)
            if validation.is_usable(obs):
                cache.set(key, obs, AQ_TTL_SECONDS)
                return obs, Resolution.LIVE
            raise ProviderUnavailable("Upstream returned no usable pollutant data.")
        except (ProviderUnavailable, ProviderNotConfigured) as exc:
            log_event(logger, logging.WARNING, "aq_provider_failed",
                      station=station.code, reason=type(exc).__name__)
            stale = cache.get_stale(key)
            if stale is not None:
                return stale[0], Resolution.CACHED
            if mode == "live":
                raise

    obs = synth_air_quality(city.slug, station.code, station.zone_type.value)
    obs = validation.validate_air_quality(obs)
    return obs, Resolution.DEMO


def fetch_weather(station: Station) -> tuple[object, str]:
    key = f"wx:{station.id}"
    mode = settings.airs_data_mode

    if mode != "demo":
        cached = cache.get(key)
        if cached is not None:
            return cached, Resolution.LIVE
        try:
            obs = weather_provider.fetch(station.latitude, station.longitude)
            obs, _ = validation.validate_weather(obs)
            cache.set(key, obs, WEATHER_TTL_SECONDS)
            return obs, Resolution.LIVE
        except (ProviderUnavailable, ProviderNotConfigured) as exc:
            log_event(logger, logging.WARNING, "weather_provider_failed",
                      station=station.code, reason=type(exc).__name__)
            stale = cache.get_stale(key)
            if stale is not None:
                return stale[0], Resolution.CACHED
            if mode == "live":
                raise

    obs = synth_weather(station.code)
    obs, _ = validation.validate_weather(obs)
    return obs, Resolution.DEMO


def fetch_traffic(station: Station) -> tuple[object, str]:
    """No free real-time traffic provider is wired yet (TomTom is a drop-in:
    implement ``TrafficProvider.fetch`` and register it here). Until then the
    traffic feature is modelled and labelled as such."""
    obs = synth_traffic(station.code, station.zone_type.value)
    obs, _ = validation.validate_traffic(obs)
    return obs, Resolution.DEMO


# ─────────────────────────── persistence ──────────────────────────────

def _provenance(resolution: str) -> Provenance:
    return Provenance.demo if resolution == Resolution.DEMO else Provenance.live


def persist_snapshot(db: Session, station: Station, city: City) -> dict:
    """Fetch + store one hourly snapshot for a station. Idempotent per hour."""
    now = datetime.now(timezone.utc)
    aq, aq_res = fetch_air_quality(station, city)
    wx, wx_res = fetch_weather(station)
    tr, tr_res = fetch_traffic(station)

    hour = aq.observed_at.replace(minute=0, second=0, microsecond=0)

    existing = db.scalar(select(AirQualityReading).where(
        AirQualityReading.station_id == station.id,
        AirQualityReading.observed_at == hour))
    if existing is None:
        db.add(AirQualityReading(
            station_id=station.id, observed_at=hour, ingested_at=now,
            provenance=_provenance(aq_res), aqi=aq.aqi,
            dominant_pollutant=aq.dominant_pollutant, pm25=aq.pm25, pm10=aq.pm10,
            no2=aq.no2, so2=aq.so2, co=aq.co, o3=aq.o3,
            sub_indices=aq.sub_indices, quality_flags=aq.quality_flags))

    wx_hour = wx.observed_at.replace(minute=0, second=0, microsecond=0)
    if db.scalar(select(WeatherReading).where(
            WeatherReading.station_id == station.id,
            WeatherReading.observed_at == wx_hour)) is None:
        db.add(WeatherReading(
            station_id=station.id, observed_at=wx_hour, ingested_at=now,
            provenance=_provenance(wx_res), temperature_c=wx.temperature_c,
            humidity_pct=wx.humidity_pct, pressure_hpa=wx.pressure_hpa,
            wind_speed_mps=wx.wind_speed_mps, wind_deg=wx.wind_deg,
            rain_1h_mm=wx.rain_1h_mm, clouds_pct=wx.clouds_pct,
            visibility_m=wx.visibility_m, condition=wx.condition,
            ventilation_index=ventilation_index(
                wx.wind_speed_mps, wx.temperature_c, _hours_local(wx_hour))))

    tr_hour = tr.observed_at.replace(minute=0, second=0, microsecond=0)
    if db.scalar(select(TrafficReading).where(
            TrafficReading.station_id == station.id,
            TrafficReading.observed_at == tr_hour)) is None:
        db.add(TrafficReading(
            station_id=station.id, observed_at=tr_hour, ingested_at=now,
            provenance=_provenance(tr_res), congestion_index=tr.congestion_index,
            speed_ratio=tr.speed_ratio, vehicle_volume_est=tr.vehicle_volume_est))

    db.commit()
    return {"station": station.code, "air_quality": aq_res,
            "weather": wx_res, "traffic": tr_res}


def ingest_city(db: Session, city: City) -> list[dict]:
    results = []
    for station in city.stations:
        if not station.is_active:
            continue
        try:
            results.append(persist_snapshot(db, station, city))
        except Exception as exc:                      # one bad station != outage
            db.rollback()
            log_event(logger, logging.ERROR, "station_ingest_failed",
                      station=station.code, error=type(exc).__name__)
            results.append({"station": station.code, "error": type(exc).__name__})
    return results
