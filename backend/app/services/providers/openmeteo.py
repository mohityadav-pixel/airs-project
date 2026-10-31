"""Open-Meteo adapters — air quality (CAMS) and weather. No API key needed.

Why this exists
---------------
WAQI gives *measured* station data but only the current hour, and many Indian
towns have no station within reach. Open-Meteo serves the Copernicus (CAMS)
atmospheric model for any coordinate: current values, a 5-day forecast and an
hourly archive back to August 2022. AIRS uses it for

* history (the year-on-year charts),
* the forecast,
* cities with no monitoring station nearby,
* weather, when no OpenWeatherMap key is configured.

Everything that comes from here is a *model* value, and is labelled that way.

Units: Open-Meteo reports every gas in ug/m3. AIRS stores gases in the US EPA
units (ppb, CO in ppm), so they are converted here at 25 degC / 1 atm.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.core import http

from app.core.errors import ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.services.providers.base import AirQualityObservation, WeatherObservation

logger = get_logger("airs.provider.openmeteo")

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
IST = ZoneInfo("Asia/Kolkata")
SOURCE_NAME = "CAMS model (Open-Meteo)"
HISTORY_START = date(2022, 8, 1)          # first day of the global archive

# ug/m3 -> ppb factor = 24.45 / molecular weight
_MW = {"no2": 46.0055, "so2": 64.066, "o3": 48.00, "co": 28.010}

AQ_VARS = ["us_aqi", "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide",
           "sulphur_dioxide", "ozone", "us_aqi_pm2_5", "us_aqi_pm10",
           "us_aqi_carbon_monoxide", "us_aqi_nitrogen_dioxide",
           "us_aqi_sulphur_dioxide", "us_aqi_ozone"]

# Open-Meteo name -> AIRS key
VAR_KEY = {"pm2_5": "pm25", "pm10": "pm10", "carbon_monoxide": "co",
           "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3"}
SUB_KEY = {"us_aqi_pm2_5": "pm25", "us_aqi_pm10": "pm10",
           "us_aqi_carbon_monoxide": "co", "us_aqi_nitrogen_dioxide": "no2",
           "us_aqi_sulphur_dioxide": "so2", "us_aqi_ozone": "o3"}


def to_airs_units(key: str, ugm3: float | None) -> float | None:
    """Convert an Open-Meteo concentration to the unit AIRS stores."""
    if ugm3 is None:
        return None
    if key in ("pm25", "pm10"):
        return round(float(ugm3), 1)
    ppb = float(ugm3) * 24.45 / _MW[key]
    return round(ppb / 1000.0, 2) if key == "co" else round(ppb, 1)


def _get(url: str, params: dict, timeout: float = 20.0) -> dict | list:
    try:
        resp = http.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        body = ""
        if isinstance(exc, httpx.HTTPStatusError):
            body = exc.response.text[:300]     # Open-Meteo puts the reason here
        log_event(logger, logging.WARNING, "openmeteo_http_error",
                  url=url.split("/")[2], error=type(exc).__name__,
                  detail=(body or str(exc))[:300])
        raise ProviderUnavailable("The Open-Meteo service is unavailable.",
                                  detail=(body or str(exc))[:300]) from exc


# ─────────────────────────── air quality ──────────────────────────────

def _obs_from_current(cur: dict) -> AirQualityObservation:
    subs = {SUB_KEY[k]: float(v) for k, v in cur.items()
            if k in SUB_KEY and v is not None}
    conc = {VAR_KEY[k]: to_airs_units(VAR_KEY[k], v) for k, v in cur.items()
            if k in VAR_KEY}
    dominant = max(subs, key=subs.get) if subs else None
    ts = cur.get("time")
    try:
        observed = (datetime.fromisoformat(ts).replace(tzinfo=IST)
                    .astimezone(timezone.utc)) if ts else datetime.now(timezone.utc)
    except ValueError:
        observed = datetime.now(timezone.utc)
    aqi = cur.get("us_aqi")
    return AirQualityObservation(
        observed_at=observed, aqi=float(aqi) if aqi is not None else None,
        dominant_pollutant=dominant, sub_indices=subs,
        source_name=SOURCE_NAME, provenance="live",
        quality_flags=["source:cams"], **conc)


class OpenMeteoAirProvider:
    """Same interface as ``WaqiProvider`` so ingestion can fall back to it."""
    name = SOURCE_NAME

    def available(self) -> bool:
        return True

    def fetch(self, lat: float, lon: float,
              keyword: str | None = None) -> AirQualityObservation:
        payload = _get(AQ_URL, {"latitude": lat, "longitude": lon,
                                "current": ",".join(AQ_VARS),
                                "timezone": "Asia/Kolkata",
                                "domains": "cams_global"})
        cur = (payload or {}).get("current") if isinstance(payload, dict) else None
        if not cur or cur.get("us_aqi") is None:
            raise ProviderUnavailable("The CAMS model returned no data here.")
        return _obs_from_current(cur)


def current_many(coords: list[tuple[float, float]]) -> list[dict | None]:
    """Current modelled AQ for many points in one request per 50 points."""
    out: list[dict | None] = []
    for i in range(0, len(coords), 50):
        chunk = coords[i:i + 50]
        payload = _get(AQ_URL, {
            "latitude": ",".join(f"{la:.4f}" for la, _ in chunk),
            "longitude": ",".join(f"{lo:.4f}" for _, lo in chunk),
            "current": ",".join(AQ_VARS), "timezone": "Asia/Kolkata",
            "domains": "cams_global"}, timeout=30.0)
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            out.append((item or {}).get("current"))
    return out


def hourly_aqi_many(coords: list[tuple[float, float]], past_days: int = 5
                    ) -> list[dict | None]:
    """Hourly US AQI (past days + today) for many points, 50 per request."""
    out: list[dict | None] = []
    for i in range(0, len(coords), 50):
        chunk = coords[i:i + 50]
        payload = _get(AQ_URL, {
            "latitude": ",".join(f"{la:.4f}" for la, _ in chunk),
            "longitude": ",".join(f"{lo:.4f}" for _, lo in chunk),
            "hourly": "us_aqi", "timezone": "Asia/Kolkata", "domains": "cams_global",
            "past_days": past_days, "forecast_days": 1}, timeout=45.0)
        items = payload if isinstance(payload, list) else [payload]
        out.extend((item or {}).get("hourly") for item in items)
        if i + 50 < len(coords):
            import time as _t
            _t.sleep(0.4)                      # stay under the per-minute limit
    return out


def hourly_air_quality(lat: float, lon: float, *, start: date | None = None,
                       end: date | None = None, past_days: int | None = None,
                       forecast_days: int | None = None) -> dict:
    """Hourly model series. Returns Open-Meteo's ``hourly`` block (local time)."""
    params: dict = {"latitude": lat, "longitude": lon,
                    "hourly": ",".join(AQ_VARS), "timezone": "Asia/Kolkata",
                    "domains": "cams_global"}
    if start and end:
        params.update(start_date=start.isoformat(), end_date=end.isoformat())
    if past_days is not None:
        params["past_days"] = past_days
    if forecast_days is not None:
        params["forecast_days"] = forecast_days
    payload = _get(AQ_URL, params, timeout=45.0)
    hourly = (payload or {}).get("hourly") if isinstance(payload, dict) else None
    if not hourly or not hourly.get("time"):
        raise ProviderUnavailable("The CAMS model returned no history here.")
    return hourly


# ─────────────────────────── weather ──────────────────────────────────

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
    82: "Violent showers", 85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail",
}

_W_CURRENT = ["temperature_2m", "relative_humidity_2m", "apparent_temperature",
              "surface_pressure", "wind_speed_10m", "wind_direction_10m",
              "precipitation", "cloud_cover", "weather_code", "is_day",
              "uv_index", "visibility"]


def weather_bundle(lat: float, lon: float, days: int = 6) -> dict:
    """Current conditions + daily outlook in one call.

    Falls back to a minimal request if the full one is rejected, so one
    variable the API stops supporting cannot blank the whole weather card.
    """
    try:
        return _weather_full(lat, lon, days)
    except ProviderUnavailable:
        return _get(WEATHER_URL, {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                       "wind_direction_10m,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "wind_speed_unit": "ms", "timezone": "Asia/Kolkata",
            "forecast_days": days})  # type: ignore[return-value]


def _weather_full(lat: float, lon: float, days: int) -> dict:
    return _get(WEATHER_URL, {
        "latitude": lat, "longitude": lon, "current": ",".join(_W_CURRENT),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,uv_index_max,wind_speed_10m_max",
        "wind_speed_unit": "ms", "timezone": "Asia/Kolkata",
        "forecast_days": days, "past_days": 1})  # type: ignore[return-value]


class OpenMeteoWeatherProvider:
    name = "Open-Meteo"

    def available(self) -> bool:
        return True

    def fetch(self, lat: float, lon: float) -> WeatherObservation:
        payload = _get(WEATHER_URL, {"latitude": lat, "longitude": lon,
                                     "current": ",".join(_W_CURRENT),
                                     "wind_speed_unit": "ms",
                                     "timezone": "Asia/Kolkata"})
        cur = (payload or {}).get("current") if isinstance(payload, dict) else None
        if not cur:
            raise ProviderUnavailable("The weather model returned no data.")
        ts = cur.get("time")
        try:
            observed = (datetime.fromisoformat(ts).replace(tzinfo=IST)
                        .astimezone(timezone.utc))
        except (TypeError, ValueError):
            observed = datetime.now(timezone.utc)
        return WeatherObservation(
            observed_at=observed, temperature_c=cur.get("temperature_2m"),
            humidity_pct=cur.get("relative_humidity_2m"),
            pressure_hpa=cur.get("surface_pressure"),
            wind_speed_mps=cur.get("wind_speed_10m"),
            wind_deg=cur.get("wind_direction_10m"),
            rain_1h_mm=cur.get("precipitation") or 0.0,
            clouds_pct=cur.get("cloud_cover"),
            visibility_m=cur.get("visibility"),
            condition=WEATHER_CODES.get(cur.get("weather_code") or -1),
            source_name="Open-Meteo", provenance="live")
