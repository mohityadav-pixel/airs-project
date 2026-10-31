"""City-level live air quality, national overview, history and forecast.

This is the layer the redesigned front end reads. It answers each question
from the best source that can actually answer it:

=====================  ==============================================  ==========
question               source                                          kind
=====================  ==============================================  ==========
AQI right now          mean of the fresh WAQI stations in the city     observed
... no station nearby  CAMS model (Open-Meteo)                         estimated
pollutant breakdown    WAQI feeds of the nearest stations              observed
weather                Open-Meteo                                      observed
last 24 h / forecast   CAMS, calibrated to the live station average    estimated
history (2022 → now)   CAMS archive, calibrated when AIRS has enough   estimated
                       stored station data to do so honestly
=====================  ==============================================  ==========

Every payload says which of these it used.
"""
from __future__ import annotations

import json
import logging
import math
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import REPO_ROOT, settings
from app.core.errors import ProviderNotConfigured, ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.db.india_cities import METRO_RADIUS_KM, STATE_OF
from app.db.models import AirQualityReading, City, Provenance, Station
from app.domain.aqi import (POLLUTANT_LABELS, POLLUTANT_UNITS_US, categorize,
                            concentration_to_index, index_to_concentration)
from app.services.providers import openaq, openmeteo
from app.services.providers.waqi import WaqiProvider, WaqiStation, haversine_km

logger = get_logger("airs.live")
IST = ZoneInfo("Asia/Kolkata")
POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")
HISTORY_DIR = REPO_ROOT / "data" / "history_cache"

waqi = WaqiProvider()

METRICS = {
    "aqi": ("AQI (US)", ""), "pm25": ("PM2.5", "µg/m³"), "pm10": ("PM10", "µg/m³"),
    "co": ("CO", "ppm"), "no2": ("NO₂", "ppb"), "so2": ("SO₂", "ppb"),
    "o3": ("O₃", "ppb"),
}
# column order inside the cached daily rows
_COLS = ["aqi", "aqi_max", "pm25", "pm10", "co", "no2", "so2", "o3"]


# ─────────────────────────── helpers ──────────────────────────────────

def category(aqi: float | None) -> dict | None:
    cat = categorize(aqi)
    if cat is None:
        return None
    return {"key": cat.key, "label": cat.label, "color": cat.color,
            "advice": cat.short_advice}


def _r(value: float | None, nd: int = 0):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(value) if nd == 0 else round(value, nd)


def _now_ist() -> datetime:
    return datetime.now(IST)


def city_meta(city: City) -> dict:
    return {"slug": city.slug, "name": city.name,
            "state": STATE_OF.get(city.slug), "latitude": city.latitude,
            "longitude": city.longitude}


def _radius(city: City) -> float:
    return METRO_RADIUS_KM.get(city.slug, 15.0)


def _select_stations(city: City, pool: list, max_age: float = 3.0,
                     radius: float | None = None, tight: bool = True) -> list:
    """The stations that honestly represent this city.

    ``pool`` mixes WAQI and OpenAQ stations (both expose lat, lon, aqi and
    age_hours()). Small towns next to big ones (Ghaziabad beside Delhi) must
    not inherit the neighbour's stations, so a tight 10 km ring is preferred
    whenever it has any station in it; the wider ring is used only when it is
    empty.
    """
    radius = radius or _radius(city)
    lat, lon = city.latitude, city.longitude
    dlat = radius / 111.0
    dlon = radius / (111.0 * max(math.cos(math.radians(lat)), 0.2))
    near: list = []
    for st in pool:
        if abs(st.lat - lat) > dlat or abs(st.lon - lon) > dlon:
            continue
        a = st.aqi
        # Below ~12 is implausible for an Indian city and in practice means a
        # faulty or indoor low-cost sensor (one read AQI 6 in Ahmedabad).
        if a is None or a < 12 or a > 999:
            continue
        age = st.age_hours()
        if age is None:
            if max_age > 3.0 or st.source != "WAQI":
                continue
        elif age > max_age or age < -2:
            continue
        d = haversine_km(lat, lon, st.lat, st.lon)
        if d <= radius:
            near.append((st, d))
    near.sort(key=lambda p: p[1])
    # the same physical station can be listed by both WAQI and OpenAQ
    deduped: list = []
    for st, d in near:
        twin = next((i for i, (o, _) in enumerate(deduped)
                     if haversine_km(o.lat, o.lon, st.lat, st.lon) < 0.5), None)
        if twin is None:
            deduped.append((st, d))
        elif (st.age_hours() or 99) < (deduped[twin][0].age_hours() or 99):
            deduped[twin] = (st, d)
    near = deduped
    if tight and city.slug not in METRO_RADIUS_KM:
        ring = [p for p in near if p[1] <= 10.0]
        near = ring if ring else near[:1]
    if len(near) >= 3:
        med = statistics.median(st.aqi for st, _ in near)
        near = [p for p in near if p[0].aqi <= max(med * 3, med + 150)]
    return near


REGIONAL_KM = 200.0   # fresh stations this far away still say something
RECENT_KM = 60.0      # a station's last reading is used within this distance


def _cap_model(city: City, value: float | None) -> float | None:
    """The CAMS model occasionally invents a dust storm (Hisar: 465 when the
    stations said 80). Never let it exceed 1.3x the worst *measured* city
    within 400 km."""
    if value is None:
        return None
    india = cache.get_stale("live:india")
    if not india:
        return value
    near = [r["aqi"] for r in india[0].get("cities", [])
            if r.get("source") == "measured" and r.get("aqi")
            and haversine_km(city.latitude, city.longitude,
                             r["latitude"], r["longitude"]) <= 400]
    return min(value, max(near) * 1.15) if near else value


def estimate_without_station(city: City, pool: list, cams_aqi: float | None,
                             cams_hourly: dict | None = None) -> tuple:
    """One rule, used by the city page AND the national ranking, so a city
    shows the same number in both places. Returns (aqi, source, label, shown).

      a) live stations within 200 km, distance-weighted;
      b) the CAMS model *corrected* by nearby stations' recent readings: each
         station reading is compared with what the model said at that same
         hour, and the median ratio is applied to the model now. This keeps
         today's weather in the answer instead of freezing a 3-day-old value;
      c) the raw model, capped by nearby measured cities.
    """
    regional = _select_stations(city, pool, max_age=3.0, radius=REGIONAL_KM,
                                tight=False) if pool else []
    if len(regional) >= 2 or (regional and regional[0][1] <= 60):
        use = regional[:12]
        w = [1 / max(d, 5.0) ** 2 for _, d in use]
        aqi = sum(a * st.aqi for a, (st, _) in zip(w, use)) / sum(w)
        label = (f"Estimated from {len(use)} live station{'' if len(use) == 1 else 's'} "
                 f"{use[0][1]:.0f}–{use[-1][1]:.0f} km away")
        return aqi, "calibrated", label, use
    recent = _select_stations(city, pool, max_age=120.0, radius=RECENT_KM,
                              tight=False)[:6] if pool else []
    if recent and cams_aqi:
        ratios = []
        for st, _ in recent:
            then = _cams_at(cams_hourly, st.observed_at) if st.observed_at else None
            if then and then.get("aqi"):
                ratios.append(st.aqi / then["aqi"])
        if len(ratios) >= 1:
            f = max(0.5, min(1.6, statistics.median(ratios)))
            age = min((st.age_hours() or 0) for st, _ in recent)
            label = (f"CAMS model corrected by {len(ratios)} nearby station"
                     f"{'' if len(ratios) == 1 else 's'} (last reported {age:.0f} h ago)")
            return _cap_model(city, cams_aqi * f), "calibrated", label, recent
    if recent and not cams_aqi:
        aqi = statistics.median(st.aqi for st, _ in recent)
        return aqi, "calibrated", "Latest readings of nearby stations", recent
    return (_cap_model(city, cams_aqi), "modelled",
            "No station anywhere near — CAMS atmospheric model", [])


def _pool() -> list:
    pool: list = list(_index())
    if openaq.available():
        try:
            pool += openaq.stations()
        except Exception as exc:             # never let OpenAQ break the page
            log_event(logger, logging.WARNING, "openaq_pool_failed",
                      error=type(exc).__name__)
    return pool


def _index() -> list[WaqiStation]:
    if not waqi.available():
        return []
    from app.core import cache as cache_module
    try:
        stations = waqi.india_index()
        cache_module.record_success("air_quality")
        return stations
    except (ProviderUnavailable, ProviderNotConfigured) as exc:
        log_event(logger, logging.WARNING, "waqi_index_failed",
                  detail=str(getattr(exc, "detail", None) or exc)[:200])
        cache_module.record_failure("air_quality", exc)
        return []


def _cams_hourly(city: City) -> dict | None:
    key = f"cams:hourly:{city.slug}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    try:
        hourly = openmeteo.hourly_air_quality(city.latitude, city.longitude,
                                              past_days=5, forecast_days=5)
    except ProviderUnavailable:
        stale = cache.get_stale(key)
        return stale[0] if stale else None
    cache.set(key, hourly, 1800)
    return hourly


def _weather(city: City) -> dict | None:
    key = f"wx:bundle:{city.slug}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    try:
        bundle = openmeteo.weather_bundle(city.latitude, city.longitude)
    except ProviderUnavailable:
        stale = cache.get_stale(key)
        return stale[0] if stale else None
    cache.set(key, bundle, 1200)
    return bundle


def _hour_key(dt: datetime) -> str:
    return dt.astimezone(IST).strftime("%Y-%m-%dT%H:00")


# ─────────────────────────── one city, now ────────────────────────────

def city_live(db: Session, city: City) -> dict:
    key = f"live:city:{city.slug}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    payload = _build_city_live(db, city)
    cache.set(key, payload, 300)
    return payload


def _station_row(st, d: float) -> dict:
    return {
        "uid": st.uid, "name": st.name.split(",")[0].strip(),
        "full_name": st.name, "latitude": st.lat, "longitude": st.lon,
        "aqi": _r(st.aqi), "category": category(st.aqi),
        "distance_km": round(d, 1), "network": st.source,
        "fresh": (st.age_hours() is None or st.age_hours() <= 3),
        "observed_at": st.observed_at.isoformat() if st.observed_at else None,
    }


def _regional_factor(city: City) -> tuple[float, int]:
    """Model/station ratio of nearby measured cities, from the national view."""
    india = cache.get_stale("live:india")
    if not india:
        return 1.0, 0
    ratios = []
    for row in india[0].get("cities", []):
        r = row.get("model_ratio")
        if r and row.get("source") == "measured":
            if haversine_km(city.latitude, city.longitude,
                            row["latitude"], row["longitude"]) <= 300:
                ratios.append(r)
    if len(ratios) >= 2:
        return max(0.25, min(3.0, statistics.median(ratios))), len(ratios)
    return 1.0, 0


def _build_city_live(db: Session, city: City) -> dict:
    now = _now_ist()
    pool = _pool()
    chosen = _select_stations(city, pool) if pool else []

    feeds = []
    waqi_chosen = [st for st, _ in chosen if st.source == "WAQI"]
    if waqi_chosen:
        with ThreadPoolExecutor(max_workers=6) as pool_ex:
            futures = [pool_ex.submit(waqi.station_feed, st.uid) for st in waqi_chosen[:10]]
            for f in futures:
                try:
                    feeds.append(f.result())
                except Exception:          # one silent station is not an outage
                    pass

    cams = _cams_hourly(city)
    cams_now = _cams_at(cams, now)
    shown = chosen
    anchors_used = 0

    if chosen:
        source = "measured"
        aqi = statistics.fmean(st.aqi for st, _ in chosen)
        factor = 1.0
        if cams_now and cams_now.get("aqi"):
            factor = max(0.25, min(3.0, aqi / cams_now["aqi"]))
        label = "Average of {} monitoring station{}".format(
            len(chosen), "" if len(chosen) == 1 else "s")
    else:
        cams_aqi = cams_now.get("aqi") if cams_now else None
        aqi, source, label, shown = estimate_without_station(city, pool, cams_aqi, cams)
        anchors_used = len(shown)
        factor = max(0.2, min(3.0, aqi / cams_aqi)) if aqi and cams_aqi else 1.0

    pollutants = _pollutants(feeds, chosen if not feeds else [],
                             cams_now if not feeds else None, factor)
    dominant = max(pollutants, key=lambda p: p["sub_index"] or 0)["key"] \
        if pollutants else None

    past = _past_24h(db, city, cams, now, factor)
    yesterday = next((p for p in past if p["hours_ago"] == 24), None)
    change_pct = None
    if yesterday and yesterday["aqi"] and aqi:
        change_pct = round((aqi - yesterday["aqi"]) / yesterday["aqi"] * 100, 1)
    values_24h = [p["aqi"] for p in past if p["aqi"] is not None] + \
        ([aqi] if aqi is not None else [])

    newest = max((st.observed_at for st, _ in chosen if st.observed_at),
                 default=None)
    networks = sorted({st.source for st, _ in chosen})

    return {
        "city": city_meta(city),
        "aqi": _r(aqi), "category": category(aqi),
        "source": source, "source_label": label,
        "station_count": len(chosen),
        "stations": [_station_row(st, d) for st, d in shown],
        "dominant_pollutant": dominant,
        "pollutants": pollutants,
        "weather": _weather_now(_weather(city)),
        "yesterday": {"aqi": _r(yesterday["aqi"]) if yesterday else None,
                      "change_pct": change_pct},
        "range_24h": {"min": _r(min(values_24h)) if values_24h else None,
                      "max": _r(max(values_24h)) if values_24h else None},
        "past_24h": past,
        "calibration_factor": round(factor, 2),
        "calibration_anchors": anchors_used,
        "observed_at": (newest or now).isoformat(),
        "generated_at": now.isoformat(),
        "provenance": _prov(
            "observed" if source == "measured" else "estimated",
            (" + ".join(f"{n} stations" for n in networks) if source == "measured"
             else f"{openmeteo.SOURCE_NAME}, calibrated" if source == "calibrated"
             else openmeteo.SOURCE_NAME),
            newest,
            note=None if source == "measured" else label),
    }


def _prov(kind: str, source: str, observed_at: datetime | None = None,
          note: str | None = None, mode: str | None = None) -> dict:
    if mode is None:
        mode = getattr(settings, "airs_data_mode", "live")
    return {"kind": kind, "mode": mode, "source": source,
            "observed_at": observed_at.isoformat() if observed_at else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": note, "is_stale": False}


def _cams_at(hourly: dict | None, when: datetime) -> dict | None:
    if not hourly:
        return None
    try:
        i = hourly["time"].index(_hour_key(when))
    except ValueError:
        return None
    row = {"aqi": hourly["us_aqi"][i]}
    for om, key in openmeteo.VAR_KEY.items():
        if om in hourly:
            row[key] = openmeteo.to_airs_units(key, hourly[om][i])
    for om, key in openmeteo.SUB_KEY.items():
        if om in hourly:
            row[f"sub_{key}"] = hourly[om][i]
    return row


def _pollutants(feeds: list, oaq: list, cams_row: dict | None,
                factor: float = 1.0) -> list[dict]:
    """Per-pollutant values. WAQI feeds first, then OpenAQ PM, then the model
    (with its particulates scaled by the station calibration factor)."""
    oa = [st for st, _ in oaq if st.source == "OpenAQ"] if oaq else []
    out = []
    for key in POLLUTANTS:
        sub = conc = None
        n = 0
        if feeds:
            subs = [f.sub_indices.get(key) for f in feeds
                    if f.sub_indices.get(key) is not None]
            if subs:
                sub = statistics.fmean(subs)
                conc = index_to_concentration(key, sub)
                n = len(subs)
        if sub is None and oa and key in ("pm25", "pm10"):
            vals = [getattr(st, key) for st in oa if getattr(st, key) is not None]
            if vals:
                conc = statistics.fmean(vals)
                sub = concentration_to_index(key, conc)
                n = len(vals)
        if sub is None and cams_row:
            conc = cams_row.get(key)
            if conc is not None and key in ("pm25", "pm10"):
                conc = conc * factor
                sub = concentration_to_index(key, conc)
            else:
                sub = cams_row.get(f"sub_{key}")
                if sub is None and conc is not None:
                    sub = concentration_to_index(key, conc)
        if conc is None and sub is None:
            continue
        out.append({"key": key, "label": POLLUTANT_LABELS[key],
                    "concentration": _r(conc, 2 if key == "co" else 1),
                    "unit": POLLUTANT_UNITS_US[key], "sub_index": _r(sub),
                    "category": category(sub), "stations": n})
    out.sort(key=lambda p: p["sub_index"] or 0, reverse=True)
    return out


def _measured_hourly(db: Session, city: City, since: datetime) -> dict[str, float]:
    """Stored *station* readings for the city, averaged per hour."""
    station_ids = [s.id for s in city.stations]
    if not station_ids:
        return {}
    rows = db.scalars(select(AirQualityReading).where(
        AirQualityReading.station_id.in_(station_ids),
        AirQualityReading.provenance == Provenance.live,
        AirQualityReading.observed_at >= since.astimezone(timezone.utc)))
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        # Only rows stamped by the fixed station matcher count: readings stored
        # before it could belong to a station in a different city.
        if r.aqi is None or "source:waqi" not in (r.quality_flags or []):
            continue
        ts = r.observed_at if r.observed_at.tzinfo else \
            r.observed_at.replace(tzinfo=timezone.utc)
        buckets[_hour_key(ts)].append(r.aqi)
    return {k: statistics.fmean(v) for k, v in buckets.items()}


def _past_24h(db: Session, city: City, cams: dict | None, now: datetime,
              factor: float) -> list[dict]:
    measured = _measured_hourly(db, city, now - timedelta(hours=26))
    out = []
    for h in range(24, 0, -1):
        at = now - timedelta(hours=h)
        k = _hour_key(at)
        if k in measured:
            out.append({"at": k, "hours_ago": h, "aqi": _r(measured[k]),
                        "kind": "observed"})
            continue
        row = _cams_at(cams, at)
        value = row["aqi"] * factor if row and row.get("aqi") is not None else None
        out.append({"at": k, "hours_ago": h, "aqi": _r(value), "kind": "estimated"})
    return out


def _weather_now(bundle: dict | None) -> dict | None:
    if not bundle:
        return None
    cur = bundle.get("current") or {}
    daily = bundle.get("daily") or {}
    days = []
    today = _now_ist().date().isoformat()
    for i, d in enumerate(daily.get("time") or []):
        if d < today:
            continue
        days.append({
            "date": d,
            "code": daily["weather_code"][i],
            "condition": openmeteo.WEATHER_CODES.get(daily["weather_code"][i]),
            "t_max": daily["temperature_2m_max"][i],
            "t_min": daily["temperature_2m_min"][i],
            "rain_chance": (daily.get("precipitation_probability_max") or [None] * 99)[i],
            "uv_max": (daily.get("uv_index_max") or [None] * 99)[i],
            "wind_max": (daily.get("wind_speed_10m_max") or [None] * 99)[i],
        })
    return {
        "temperature_c": cur.get("temperature_2m"),
        "feels_like_c": cur.get("apparent_temperature"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "pressure_hpa": cur.get("surface_pressure"),
        "wind_speed_mps": cur.get("wind_speed_10m"),
        "wind_deg": cur.get("wind_direction_10m"),
        "rain_mm": cur.get("precipitation"),
        "cloud_pct": cur.get("cloud_cover"),
        "uv_index": cur.get("uv_index"),
        "visibility_m": cur.get("visibility"),
        "is_day": bool(cur.get("is_day", 1)),
        "code": cur.get("weather_code"),
        "condition": openmeteo.WEATHER_CODES.get(cur.get("weather_code")),
        "daily": days,
    }


# ─────────────────────────── forecast ─────────────────────────────────

def city_forecast(db: Session, city: City) -> dict:
    live = city_live(db, city)
    cams = _cams_hourly(city)
    now = _now_ist().replace(minute=0, second=0, microsecond=0)
    calibrated = (live.get("source") == "measured" and bool(live.get("calibration_factor") and live.get("calibration_factor") != 1.0))
    factor = live.get("calibration_factor") if calibrated else 1.0
    hours = []
    if cams:
        for i, t in enumerate(cams["time"]):
            at = datetime.fromisoformat(t).replace(tzinfo=IST)
            ahead = (at - now).total_seconds() / 3600
            if ahead < 1 or ahead > 120:
                continue
            raw = cams["us_aqi"][i]
            if raw is None:
                continue
            # the station/model gap shrinks with lead time: trust the model's
            # shape, lean on the stations for the level near "now"
            w = math.exp(-ahead / 36.0)
            value = raw * (1 + (factor - 1) * w)
            hours.append({"at": t, "hours_ahead": int(ahead), "aqi": _r(value),
                          "raw_model_aqi": _r(raw),
                          "kind": "predicted",
                          "pm25": openmeteo.to_airs_units("pm25", cams["pm2_5"][i]),
                          "pm10": openmeteo.to_airs_units("pm10", cams["pm10"][i]),
                          "category": category(value)})
    by_day: dict[str, list[float]] = defaultdict(list)
    for h in hours:
        by_day[h["at"][:10]].append(h["aqi"])
    wx = (live.get("weather") or {}).get("daily") or []
    wx_by_day = {d["date"]: d for d in wx}
    days = [{"date": d, "min": min(v), "max": max(v),
             "avg": _r(statistics.fmean(v)), "category": category(statistics.fmean(v)),
             "weather": wx_by_day.get(d)} for d, v in sorted(by_day.items())]
    peak = max(hours, key=lambda h: h["aqi"] or 0) if hours else None
    best = min(hours[:48], key=lambda h: h["aqi"] or 1e9) if hours else None
    source_label = (
        "Copernicus (CAMS) forecast via Open-Meteo, calibrated to live stations"
        if calibrated else
        "Copernicus (CAMS) atmospheric model forecast via Open-Meteo"
    )
    prov_note = (
        "The Copernicus atmospheric model's 5-day forecast, scaled to "
        "match today's ground station average and relaxing back to the raw model."
        if calibrated else
        "Copernicus (CAMS) atmospheric numerical transport model forecast. Not calibrated to ground stations because no live stations reported recently."
    )
    return {
        "city": city_meta(city), "current_aqi": live.get("aqi"),
        "hours": hours, "days": days, "peak": peak, "best_window": best,
        "calibration_factor": factor,
        "provenance": _prov(
            "predicted", source_label, note=prov_note, mode="live"),
    }


# ─────────────────────────── the whole country ────────────────────────

def india_live(db: Session, cities: list[City]) -> dict:
    hit = cache.get("live:india")
    if hit is not None:
        return hit
    index = _index()
    pool = _pool()
    rows = []
    for city in cities:
        chosen = _select_stations(city, pool) if pool else []
        if chosen:
            value = statistics.fmean(st.aqi for st, _ in chosen)
            newest = max((st.observed_at for st, _ in chosen if st.observed_at),
                         default=None)
            rows.append({**city_meta(city), "aqi": _r(value),
                         "category": category(value), "source": "measured",
                         "station_count": len(chosen), "_measured": value,
                         "observed_at": newest.isoformat() if newest else None})
        else:
            rows.append({**city_meta(city), "aqi": None, "category": None,
                         "source": "modelled", "station_count": 0,
                         "observed_at": None})
    # One model series per city (past 5 days + today): the current hour fills
    # the gaps, the past hours let recent station readings correct it. Kept
    # for 30 min, and the last good copy is reused if Open-Meteo is refusing
    # requests, so a rate limit never empties the map.
    hourly_by_slug: dict = cache.get("cams:hourly-many") or {}
    if not hourly_by_slug:
        try:
            series = openmeteo.hourly_aqi_many([(c.latitude, c.longitude) for c in cities])
            for c, h in zip(cities, series):
                if h and h.get("time"):
                    hourly_by_slug[c.slug] = {"time": h["time"], "us_aqi": h["us_aqi"]}
        except ProviderUnavailable as exc:
            log_event(logger, logging.WARNING, "cams_many_failed",
                      detail=str(getattr(exc, "detail", None) or exc)[:200])
        if len(hourly_by_slug) >= len(cities) * 0.8:
            cache.set("cams:hourly-many", hourly_by_slug, 1800)
        else:
            stale = cache.get_stale("cams:hourly-many")
            if stale:
                hourly_by_slug = {**stale[0], **hourly_by_slug}
    now = _now_ist()
    currents = []
    for c in cities:
        row_now = _cams_at(hourly_by_slug.get(c.slug), now)
        currents.append({"us_aqi": row_now["aqi"], "time": _hour_key(now)}
                        if row_now and row_now.get("aqi") is not None else None)
    missing_ix = [i for i, cur in enumerate(currents) if cur is None]
    if missing_ix:                               # second chance: the light endpoint
        try:
            extra = openmeteo.current_many(
                [(cities[i].latitude, cities[i].longitude) for i in missing_ix])
            for i, cur in zip(missing_ix, extra):
                currents[i] = cur
        except ProviderUnavailable:
            pass
    for row, cur in zip(rows, currents):
        row["_model"] = cur.get("us_aqi") if cur else None
        if row["source"] == "measured" and row["_model"]:
            row["model_ratio"] = row["_measured"] / row["_model"]
    ratios_all = [r["model_ratio"] for r in rows if r.get("model_ratio")]

    for row, cur in zip(rows, currents):
        if row["source"] == "measured":
            continue
        near = [r["model_ratio"] for r in rows if r.get("model_ratio")
                and haversine_km(row["latitude"], row["longitude"],
                                 r["latitude"], r["longitude"]) <= 300]
        city_obj = next(c for c in cities if c.slug == row["slug"])
        value, row["source"], _, _ = estimate_without_station(
            city_obj, pool, row["_model"], hourly_by_slug.get(row["slug"]))
        row["aqi"] = _r(value)
        row["category"] = category(value)
        row["observed_at"] = (f"{cur['time']}:00+05:30" if cur and cur.get("time")
                              else None)
    for row in rows:
        row.pop("_measured", None)
        row.pop("_model", None)

    ranked = sorted([r for r in rows if r["aqi"] is not None],
                    key=lambda r: r["aqi"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    by_cat: dict[str, int] = defaultdict(int)
    for r in ranked:
        by_cat[r["category"]["key"]] += 1
    states: dict[str, list[float]] = defaultdict(list)
    for r in ranked:
        if r.get("state"):
            states[r["state"]].append(r["aqi"])
    state_rows = sorted(({"state": s, "aqi": _r(statistics.fmean(v)),
                          "cities": len(v), "category": category(statistics.fmean(v))}
                         for s, v in states.items()),
                        key=lambda r: r["aqi"], reverse=True)
    measured = sum(1 for r in ranked if r["source"] == "measured")
    calibrated = sum(1 for r in ranked if r["source"] == "calibrated")
    prov_kind = "observed" if measured >= len(ranked) * 0.5 else "estimated"
    prov_source = ("WAQI + OpenAQ stations; CAMS model calibrated to them"
                   if measured
                   else "Copernicus CAMS atmospheric model estimates")
    payload = {
        "cities": rows, "worst": ranked[:10],
        "cleanest": list(reversed(ranked[-10:])),
        "national_average": _r(statistics.fmean(r["aqi"] for r in ranked))
        if ranked else None,
        "reporting_cities": len(ranked), "total_cities": len(rows),
        "measured_cities": measured,
        "calibrated_cities": calibrated,
        "modelled_cities": len(ranked) - measured - calibrated,
        "station_count": sum(1 for st in pool
                             if st.aqi and (st.age_hours() or 0) <= 3),
        "openaq": openaq.status() if openaq.available() else None,
        "by_category": dict(by_cat), "states": state_rows,
        "generated_at": _now_ist().isoformat(),
        "provenance": _prov(prov_kind, prov_source),
    }
    # Only keep a national view that actually had station data behind it; a
    # moment of lost Wi-Fi must not pin 273 raw-model numbers for 10 minutes.
    if measured and len(ranked) >= len(rows) * 0.9:
        cache.set("live:india", payload, 600)
    elif ranked:
        cache.set("live:india", payload, 45)
    return payload


# ─────────────────────────── history ──────────────────────────────────

def _year_daily(city: City, year: int) -> dict[str, list]:
    """Daily means for one calendar year, cached on disk.

    Past years never change, so they are fetched once. The current year is
    re-fetched at most every three hours.
    """
    today = _now_ist().date()
    start = max(date(year, 1, 1), openmeteo.HISTORY_START)
    end = min(date(year, 12, 31), today)
    if start > end:
        return {}
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = HISTORY_DIR / f"{city.slug}-{year}.json"
    if path.exists():
        age = time.time() - path.stat().st_mtime
        complete = year < today.year
        if complete or age < 3 * 3600:
            try:
                return json.loads(path.read_text())
            except (OSError, ValueError):
                pass
    hourly = openmeteo.hourly_air_quality(city.latitude, city.longitude,
                                          start=start, end=end)
    sums: dict[str, list[list[float]]] = defaultdict(lambda: [[] for _ in range(7)])
    for i, t in enumerate(hourly["time"]):
        day = t[:10]
        vals = [hourly["us_aqi"][i], hourly["pm2_5"][i], hourly["pm10"][i],
                hourly["carbon_monoxide"][i], hourly["nitrogen_dioxide"][i],
                hourly["sulphur_dioxide"][i], hourly["ozone"][i]]
        for j, v in enumerate(vals):
            if v is not None:
                sums[day][j].append(v)
    out: dict[str, list] = {}
    keys = ["aqi", "pm25", "pm10", "co", "no2", "so2", "o3"]
    for day, cols in sums.items():
        if not cols[0]:
            continue
        row = [_r(statistics.fmean(cols[0])), _r(max(cols[0]))]
        for key, col in zip(keys[1:], cols[1:]):
            mean = statistics.fmean(col) if col else None
            row.append(openmeteo.to_airs_units(key, mean) if mean is not None else None)
        out[day] = row
    try:
        path.write_text(json.dumps(out, separators=(",", ":")))
    except OSError:
        pass
    return out


def _measured_daily(db: Session, city: City, since: date) -> dict[str, float]:
    station_ids = [s.id for s in city.stations]
    if not station_ids:
        return {}
    start = datetime.combine(since, datetime.min.time(), IST).astimezone(timezone.utc)
    rows = db.scalars(select(AirQualityReading).where(
        AirQualityReading.station_id.in_(station_ids),
        AirQualityReading.provenance == Provenance.live,
        AirQualityReading.observed_at >= start))
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        # Only rows stamped by the fixed station matcher count: readings stored
        # before it could belong to a station in a different city.
        if r.aqi is None or "source:waqi" not in (r.quality_flags or []):
            continue
        ts = r.observed_at if r.observed_at.tzinfo else \
            r.observed_at.replace(tzinfo=timezone.utc)
        buckets[ts.astimezone(IST).date().isoformat()].append(r.aqi)
    # a day needs a reasonable number of hours before its mean means anything
    return {d: statistics.fmean(v) for d, v in buckets.items() if len(v) >= 6}


def city_history(db: Session, city: City, month: int | None = None,
                 metric: str = "aqi") -> dict:
    if metric not in METRICS:
        metric = "aqi"
    today = _now_ist().date()
    month = month or today.month
    years = list(range(openmeteo.HISTORY_START.year, today.year + 1))

    cache_key = f"history:{city.slug}"
    daily_by_year = cache.get(cache_key)
    if daily_by_year is None:
        daily_by_year = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {y: pool.submit(_year_daily, city, y) for y in years}
            for y, f in futures.items():
                try:
                    daily_by_year[y] = f.result()
                except ProviderUnavailable as exc:
                    log_event(logger, logging.WARNING, "history_year_failed",
                              city=city.slug, year=y,
                              detail=str(getattr(exc, "detail", None) or exc)[:200])
                    daily_by_year[y] = {}
        if any(daily_by_year.values()):
            cache.set(cache_key, daily_by_year, 1800)

    col = {"aqi": 0, "pm25": 2, "pm10": 3, "co": 4, "no2": 5, "so2": 6, "o3": 7}[metric]

    # Calibration: only from days where AIRS has real station data.
    measured = _measured_daily(db, city, today - timedelta(days=120))
    ratios = []
    for d, m in measured.items():
        row = daily_by_year.get(int(d[:4]), {}).get(d)
        if row and row[0]:
            ratios.append(m / row[0])
    factor = statistics.median(ratios) if len(ratios) >= 3 else 1.0
    factor = max(0.4, min(2.5, factor))
    scale = factor if metric == "aqi" else 1.0

    def value(y: int, d: str):
        row = daily_by_year.get(y, {}).get(d)
        if not row or row[col] is None:
            return None
        return _r(row[col] * scale, 0 if metric == "aqi" else 1)

    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    series = []
    for y in years:
        pts = []
        for day in range(1, days_in_month + 1):
            try:
                d = date(y, month, day)
            except ValueError:
                pts.append({"day": day, "value": None})
                continue
            key = d.isoformat()
            obs = measured.get(key) if metric == "aqi" else None
            pts.append({"day": day, "value": value(y, key),
                        "measured": _r(obs) if obs is not None else None})
        if any(p["value"] is not None for p in pts):
            series.append({"year": y, "days": pts})

    monthly = []
    for y in years:
        months = []
        for m in range(1, 13):
            vals = [value(y, d) for d in daily_by_year.get(y, {})
                    if int(d[5:7]) == m]
            vals = [v for v in vals if v is not None]
            months.append(_r(statistics.fmean(vals), 0 if metric == "aqi" else 1)
                          if vals else None)
        if any(v is not None for v in months):
            monthly.append({"year": y, "months": months})

    this_year = next((s for s in series if s["year"] == today.year), None)
    last_year = next((s for s in series if s["year"] == today.year - 1), None)

    def stats(s):
        if not s:
            return None
        vals = [(p["day"], p["value"]) for p in s["days"] if p["value"] is not None]
        if not vals:
            return None
        best = min(vals, key=lambda p: p[1])
        worst = max(vals, key=lambda p: p[1])
        return {"avg": _r(statistics.fmean(v for _, v in vals), 1),
                "best_day": best[0], "best": best[1],
                "worst_day": worst[0], "worst": worst[1], "days": len(vals)}

    cur_stats, prev_stats = stats(this_year), stats(last_year)
    change = None
    if cur_stats and prev_stats and prev_stats["avg"]:
        # compare like with like: only the days of this month seen so far
        n = cur_stats["days"]
        prev_vals = [p["value"] for p in last_year["days"][:n] if p["value"] is not None]
        if prev_vals:
            prev_avg = statistics.fmean(prev_vals)
            change = round((cur_stats["avg"] - prev_avg) / prev_avg * 100, 1)

    calendar = []
    for d, row in sorted(daily_by_year.get(today.year, {}).items()):
        v = _r(row[0] * factor) if row and row[0] is not None else None
        calendar.append({"date": d, "aqi": v,
                         "color": (category(v) or {}).get("color")})

    label, unit = METRICS[metric]
    calibrated = len(ratios) >= 3 and metric == "aqi"
    return {
        "city": city_meta(city), "metric": metric, "metric_label": label,
        "unit": unit, "month": month, "years": [s["year"] for s in series],
        "series": series, "monthly": monthly, "calendar": calendar,
        "summary": {"this_year": cur_stats, "last_year": prev_stats,
                    "change_vs_last_year_pct": change},
        "calibration": {"applied": calibrated, "factor": round(factor, 2),
                        "days": len(ratios)},
        "provenance": _prov(
            "estimated", openmeteo.SOURCE_NAME,
            note=("Daily means from the Copernicus (CAMS) atmospheric "
                  "reanalysis and forecast archive. "
                  + (f"Scaled by {factor:.2f} to match {len(ratios)} days of "
                     "AIRS station data." if calibrated else
                     "Raw model values — AIRS will calibrate them against "
                     "station data once the hourly ingest has stored a few "
                     "days of it."))),
    }
