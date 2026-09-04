"""Data-quality gate. Everything entering the database passes through here.

A reading is never silently dropped *and* never silently trusted: implausible
fields are nulled out and the reason is recorded in ``quality_flags``, so the
analytics layer can exclude them and an operator can see why.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.providers.base import (AirQualityObservation, TrafficObservation,
                                          WeatherObservation)

# Physically plausible envelopes. Wider than typical values on purpose — the
# goal is to catch sensor faults and unit errors, not to censor real extremes.
AQ_RANGES = {
    "pm25": (0.0, 1200.0), "pm10": (0.0, 2500.0), "no2": (0.0, 3000.0),
    "so2": (0.0, 3000.0), "co": (0.0, 100.0), "o3": (0.0, 800.0),
}
WEATHER_RANGES = {
    "temperature_c": (-40.0, 60.0), "humidity_pct": (0.0, 100.0),
    "pressure_hpa": (850.0, 1100.0), "wind_speed_mps": (0.0, 75.0),
    "wind_deg": (0.0, 360.0), "rain_1h_mm": (0.0, 400.0),
    "clouds_pct": (0.0, 100.0), "visibility_m": (0.0, 50000.0),
}

STALE_AFTER = timedelta(hours=6)


def _clamp_fields(obj, ranges: dict[str, tuple[float, float]]) -> list[str]:
    flags: list[str] = []
    for field, (lo, hi) in ranges.items():
        value = getattr(obj, field, None)
        if value is None:
            flags.append(f"{field}_missing")
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            setattr(obj, field, None)
            flags.append(f"{field}_not_numeric")
            continue
        if not (lo <= numeric <= hi):
            setattr(obj, field, None)
            flags.append(f"{field}_out_of_range")
    return flags


def validate_air_quality(obs: AirQualityObservation) -> AirQualityObservation:
    flags = list(obs.quality_flags)
    flags += _clamp_fields(obs, AQ_RANGES)

    # Cross-field consistency: the fine fraction cannot exceed the coarse total.
    if obs.pm25 is not None and obs.pm10 is not None and obs.pm25 > obs.pm10 * 1.02:
        flags.append("pm25_exceeds_pm10")

    if obs.aqi is not None and not (0 <= obs.aqi <= 900):
        obs.aqi = None
        flags.append("aqi_out_of_range")

    if is_stale(obs.observed_at):
        flags.append("stale")

    if all(getattr(obs, p) is None for p in AQ_RANGES) and obs.aqi is None:
        flags.append("empty_reading")

    obs.quality_flags = sorted(set(flags))
    return obs


def validate_weather(obs: WeatherObservation) -> tuple[WeatherObservation, list[str]]:
    flags = _clamp_fields(obs, WEATHER_RANGES)
    if is_stale(obs.observed_at):
        flags.append("stale")
    return obs, sorted(set(flags))


def validate_traffic(obs: TrafficObservation) -> tuple[TrafficObservation, list[str]]:
    flags: list[str] = []
    for field, (lo, hi) in {"congestion_index": (0.0, 1.0),
                            "speed_ratio": (0.0, 1.5),
                            "vehicle_volume_est": (0.0, 200000.0)}.items():
        value = getattr(obs, field, None)
        if value is not None and not (lo <= float(value) <= hi):
            setattr(obs, field, None)
            flags.append(f"{field}_out_of_range")
    return obs, flags


def is_stale(observed_at: datetime | None,
             max_age: timedelta = STALE_AFTER) -> bool:
    if observed_at is None:
        return True
    ts = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts > max_age


def is_usable(obs: AirQualityObservation) -> bool:
    """A reading worth storing has at least one pollutant or a headline AQI."""
    return "empty_reading" not in obs.quality_flags
