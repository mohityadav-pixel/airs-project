"""Deterministic synthetic data provider — the engine behind DEMO mode.

Design rules, because a fake data source is easy to get wrong:

* **Deterministic.** Values are a pure function of (station, timestamp), seeded
  by a hash of the station code. Reload the page and the past does not change;
  two users see the same city.
* **Internally consistent.** PM2.5 <= PM10, NO2 tracks the traffic curve, wind
  suppresses everything, and the AQI is *computed* from the concentrations with
  the same EPA function used for live data - not drawn independently.
* **Physically plausible.** Two traffic peaks a day, an overnight inversion
  build-up, a weekend dip, a slow seasonal term, and industrial/dust offsets
  that depend on the station's zone.
* **Never disguised as live.** Every row is stamped ``provenance="demo"`` and
  the API surfaces that to the UI.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone

from app.domain.aqi import concentration_to_index, overall_aqi
from app.services.providers.base import (AirQualityObservation, TrafficObservation,
                                          WeatherObservation)

IST = timezone(timedelta(hours=5, minutes=30))

# Baseline annual-mean PM2.5 (ug/m3) per city, loaded from the seed table so
# the national map shows the real geography of Indian air quality — the
# Indo-Gangetic plain far worse than the coasts and the south — rather than one
# uniform number everywhere.
from app.db.seed_data import CITY_BASELINES as CITY_BASELINE_PM25  # noqa: E402

ZONE_MULTIPLIER = {
    "traffic_corridor": 1.28, "industrial": 1.22, "commercial": 1.08,
    "mixed": 1.0, "residential": 0.92, "construction": 1.18, "green": 0.78,
}


def _seed(station_code: str) -> float:
    digest = hashlib.sha256(station_code.encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _diurnal_traffic(hour: float) -> float:
    """Two commuting peaks (~9:00 and ~19:30) on a 0..1 scale."""
    morning = math.exp(-((hour - 9.0) ** 2) / 4.5)
    evening = math.exp(-((hour - 19.5) ** 2) / 6.0)
    base = 0.18
    return min(1.0, base + 0.75 * morning + 0.95 * evening)


def _inversion_factor(hour: float) -> float:
    """Nocturnal boundary-layer collapse: pollutants concentrate 21:00-07:00."""
    if 11 <= hour <= 16:
        return 0.72
    if 7 <= hour < 11 or 16 < hour <= 19:
        return 0.96
    return 1.34


def _seasonal(day_of_year: int) -> float:
    """Indian seasonality: a winter maximum (Nov-Jan) plus an explicit monsoon
    washout (Jul-Sep), which a single cosine cannot represent — the monsoon
    trough is much deeper and sharper than a sinusoid implies."""
    winter = 1.0 + 0.55 * math.cos((day_of_year - 15) / 365.0 * 2 * math.pi)
    # Gaussian washout centred on mid-August.
    monsoon = 1.0 - 0.42 * math.exp(-((day_of_year - 225) ** 2) / 2400.0)
    return max(0.35, winter * monsoon)


def _wind_for(ts: datetime, seed: float) -> float:
    hour = ts.hour + ts.minute / 60
    daily = 1.6 + 1.5 * math.sin((hour - 7) / 24 * 2 * math.pi)
    wobble = 0.9 * math.sin(ts.timetuple().tm_yday * 0.7 + seed * 6.28)
    return round(max(0.3, daily + wobble + seed * 0.8), 2)


def _to_ist(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(IST)


def synth_air_quality(city_slug: str, station_code: str, zone: str,
                      ts: datetime | None = None) -> AirQualityObservation:
    ts = ts or datetime.now(timezone.utc)
    local = _to_ist(ts)
    seed = _seed(station_code)
    hour = local.hour + local.minute / 60

    traffic = _diurnal_traffic(hour)
    inversion = _inversion_factor(hour)
    season = _seasonal(local.timetuple().tm_yday)
    weekend = 0.86 if local.weekday() >= 5 else 1.0
    wind = _wind_for(ts, seed)
    # Capped so a dead-calm hour cannot produce an unphysical runaway.
    dispersion = min(1.35, 1.0 / (0.62 + 0.30 * min(wind, 6.0)))

    base = CITY_BASELINE_PM25.get(city_slug, 45.0)
    zone_mult = ZONE_MULTIPLIER.get(zone, 1.0)
    station_bias = 0.85 + 0.30 * seed

    pm25 = (base * zone_mult * station_bias * season * weekend
            * inversion * dispersion * (0.72 + 0.45 * traffic))
    # Coarse fraction: dust-heavy zones widen the PM10/PM2.5 ratio.
    ratio = 1.75 + (0.65 if zone in ("construction", "industrial", "traffic_corridor") else 0.15)
    pm10 = pm25 * ratio * (0.95 + 0.2 * seed)

    no2 = 14 + 48 * traffic * zone_mult * dispersion * weekend
    co = 0.35 + 1.5 * traffic * dispersion * zone_mult
    so2 = 5 + (16 if zone == "industrial" else 4) * (0.7 + 0.6 * seed) * dispersion
    # Ozone is photochemical: it peaks in the afternoon, opposite to NO2.
    o3 = max(4.0, 46 * math.exp(-((hour - 15) ** 2) / 9.0) * (1.1 - 0.35 * traffic))

    conc = {"pm25": round(pm25, 1), "pm10": round(pm10, 1), "no2": round(no2, 1),
            "so2": round(so2, 1), "co": round(co, 2), "o3": round(o3, 1)}
    subs = {k: concentration_to_index(k, v) for k, v in conc.items()}
    subs = {k: v for k, v in subs.items() if v is not None}
    aqi, dominant = overall_aqi(subs)

    return AirQualityObservation(
        observed_at=ts.replace(minute=0, second=0, microsecond=0),
        aqi=aqi, dominant_pollutant=dominant,
        pm25=conc["pm25"], pm10=conc["pm10"], no2=conc["no2"],
        so2=conc["so2"], co=conc["co"], o3=conc["o3"],
        sub_indices=subs, source_name="AIRS synthetic model",
        provenance="demo", station_ref=station_code,
    )


def synth_weather(station_code: str, ts: datetime | None = None) -> WeatherObservation:
    ts = ts or datetime.now(timezone.utc)
    local = _to_ist(ts)
    seed = _seed(station_code)
    hour = local.hour + local.minute / 60
    doy = local.timetuple().tm_yday

    seasonal_temp = 26 + 8 * math.sin((doy - 100) / 365 * 2 * math.pi)
    temp = seasonal_temp + 6.5 * math.sin((hour - 9) / 24 * 2 * math.pi) + seed * 1.5
    humidity = max(18.0, min(96.0, 62 - 0.9 * (temp - 26) + 12 * math.sin(doy / 58.0)))
    wind = _wind_for(ts, seed)

    return WeatherObservation(
        observed_at=ts.replace(minute=0, second=0, microsecond=0),
        temperature_c=round(temp, 1),
        humidity_pct=round(humidity, 1),
        pressure_hpa=round(1008 + 6 * math.cos(doy / 58.0) + seed * 2, 1),
        wind_speed_mps=wind,
        wind_deg=round((doy * 7 + hour * 11 + seed * 360) % 360, 0),
        rain_1h_mm=0.0,
        clouds_pct=round(max(0.0, min(100.0, 30 + 40 * math.sin(doy / 40.0 + seed))), 0),
        visibility_m=round(max(600.0, 9000 - 55 * max(0.0, (humidity - 45))), 0),
        condition="Haze" if humidity > 70 else "Clear",
        source_name="AIRS synthetic model", provenance="demo",
    )


def synth_traffic(station_code: str, zone: str,
                  ts: datetime | None = None) -> TrafficObservation:
    ts = ts or datetime.now(timezone.utc)
    local = _to_ist(ts)
    hour = local.hour + local.minute / 60
    seed = _seed(station_code)
    weekend = 0.72 if local.weekday() >= 5 else 1.0
    corridor = 1.25 if zone == "traffic_corridor" else (0.8 if zone == "green" else 1.0)
    congestion = min(0.98, _diurnal_traffic(hour) * corridor * weekend * (0.85 + 0.3 * seed))
    return TrafficObservation(
        observed_at=ts.replace(minute=0, second=0, microsecond=0),
        congestion_index=round(congestion, 3),
        speed_ratio=round(max(0.18, 1.0 - 0.72 * congestion), 3),
        vehicle_volume_est=round(1800 * congestion * corridor, 0),
        source_name="AIRS synthetic model", provenance="demo",
    )
