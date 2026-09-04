"""Normalised internal data model for every upstream provider.

The whole point of this module is that nothing downstream of it knows or cares
which vendor the data came from. Swapping WAQI for OpenAQ, or OpenWeatherMap
for IMD, means writing one new adapter that returns these dataclasses — no
change to the database layer, the ML pipeline, the API or the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class AirQualityObservation:
    observed_at: datetime
    aqi: float | None
    dominant_pollutant: str | None
    # concentrations in the units defined by app.domain.aqi
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    so2: float | None = None
    co: float | None = None
    o3: float | None = None
    sub_indices: dict[str, float] = field(default_factory=dict)
    source_name: str = "unknown"
    provenance: str = "live"
    station_ref: str | None = None
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class WeatherObservation:
    observed_at: datetime
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    wind_speed_mps: float | None = None
    wind_deg: float | None = None
    rain_1h_mm: float | None = None
    clouds_pct: float | None = None
    visibility_m: float | None = None
    condition: str | None = None
    source_name: str = "unknown"
    provenance: str = "live"


@dataclass
class TrafficObservation:
    observed_at: datetime
    congestion_index: float | None = None
    speed_ratio: float | None = None
    vehicle_volume_est: float | None = None
    source_name: str = "unknown"
    provenance: str = "live"


class AirQualityProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def fetch(self, lat: float, lon: float,
              keyword: str | None = None) -> AirQualityObservation: ...


class WeatherProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def fetch(self, lat: float, lon: float) -> WeatherObservation: ...
