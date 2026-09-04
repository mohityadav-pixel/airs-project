"""OpenWeatherMap adapter (current conditions).

Extends the original ``src/data_collection/fetch_weather.py`` with a derived
**ventilation index** — wind speed x an inversion proxy — because dispersion,
not emission, is what usually explains a sudden overnight AQI spike.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.errors import ProviderNotConfigured, ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.services.providers.base import WeatherObservation

logger = get_logger("airs.provider.openweather")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


class OpenWeatherProvider:
    name = "OpenWeatherMap"

    def available(self) -> bool:
        return bool(settings.openweather_api_key)

    def fetch(self, lat: float, lon: float) -> WeatherObservation:
        if not self.available():
            raise ProviderNotConfigured("Weather provider is not configured.")
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(BASE_URL, params={
                    "lat": lat, "lon": lon,
                    "appid": settings.openweather_api_key, "units": "metric"})
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            log_event(logger, logging.WARNING, "openweather_http_error",
                      error=type(exc).__name__)
            raise ProviderUnavailable(detail=str(exc)) from exc

        main = data.get("main", {})
        wind = data.get("wind", {})
        return WeatherObservation(
            observed_at=datetime.fromtimestamp(data.get("dt", 0) or 0, tz=timezone.utc),
            temperature_c=main.get("temp"),
            humidity_pct=main.get("humidity"),
            pressure_hpa=main.get("pressure"),
            wind_speed_mps=wind.get("speed"),
            wind_deg=wind.get("deg"),
            rain_1h_mm=(data.get("rain") or {}).get("1h", 0.0),
            clouds_pct=(data.get("clouds") or {}).get("all"),
            visibility_m=data.get("visibility"),
            condition=(data.get("weather") or [{}])[0].get("main"),
            source_name="OpenWeatherMap",
            provenance="live",
        )


def ventilation_index(wind_speed_mps: float | None,
                      temperature_c: float | None,
                      hour_local: int) -> float | None:
    """Crude but useful dispersion proxy in the range 0..1.

    Mixing height is not measured by free APIs, so we approximate it: nights and
    early mornings suppress vertical mixing (radiative inversion), afternoons
    enhance it. Multiplied by wind speed this tracks the "why did AQI spike at
    9 pm with no new emissions" case that citizens ask about constantly.
    """
    if wind_speed_mps is None:
        return None
    if 11 <= hour_local <= 16:
        mixing = 1.0
    elif 7 <= hour_local <= 10 or 17 <= hour_local <= 19:
        mixing = 0.6
    else:
        mixing = 0.3
    if temperature_c is not None and temperature_c < 12:
        mixing *= 0.8          # cold, stable air suppresses mixing further
    raw = min(wind_speed_mps, 8.0) / 8.0 * mixing
    return round(max(0.0, min(1.0, raw)), 3)
