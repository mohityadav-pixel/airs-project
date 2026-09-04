from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.common import resolve_city, resolve_station
from app.db.session import get_db
from app.domain.aqi import POLLUTANT_LABELS, POLLUTANT_UNITS_US, mean
from app.services import assembly, repository

router = APIRouter(prefix="/analytics", tags=["analytics"])

POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Correlation without pulling numpy into the request path."""
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n < 6:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = sum((x - mx) ** 2 for x, _ in pairs) ** 0.5
    dy = sum((y - my) ** 2 for _, y in pairs) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 3)


@router.get("/pollutants")
def pollutant_breakdown(city: str | None = None, station_id: int | None = None,
                        hours: int = Query(default=168, ge=24, le=24 * 90),
                        db: Session = Depends(get_db)) -> dict:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    rows = repository.air_quality_series(db, station.id, hours=hours)
    latest = rows[-1] if rows else None

    out = []
    for key in POLLUTANTS:
        values = [getattr(r, key) for r in rows]
        present = [v for v in values if v is not None]
        if not present:
            continue
        day = [getattr(r, key) for r in rows[-24:]]
        week = [getattr(r, key) for r in rows[-168:]]
        subs = [(r.sub_indices or {}).get(key) for r in rows]
        out.append({
            "key": key, "label": POLLUTANT_LABELS[key],
            "unit": POLLUTANT_UNITS_US[key],
            "current": getattr(latest, key, None),
            "average_24h": mean(day), "average_7d": mean(week),
            "min": min(present), "max": max(present),
            "correlation_with_aqi": _pearson([r.aqi for r in rows], values),
            "times_dominant_pct": round(
                100 * sum(1 for r in rows if r.dominant_pollutant == key)
                / max(len(rows), 1), 1),
            "share_of_aqi_now": (
                round((latest.sub_indices or {}).get(key, 0) / latest.aqi * 100, 1)
                if latest and latest.aqi and (latest.sub_indices or {}).get(key)
                else None),
        })
    out.sort(key=lambda p: p["share_of_aqi_now"] or 0, reverse=True)
    return {"station": assembly.station_out(station).model_dump(),
            "window_hours": hours, "pollutants": out}


@router.get("/correlations")
def correlations(city: str | None = None, station_id: int | None = None,
                 hours: int = Query(default=336, ge=48, le=24 * 90),
                 db: Session = Depends(get_db)) -> dict:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    aq = repository.air_quality_series(db, station.id, hours=hours)
    wx = {w.observed_at: w for w in repository.weather_series(db, station.id, hours=hours)}
    tr = {t.observed_at: t for t in repository.traffic_series(db, station.id, hours=hours)}

    aqi = [r.aqi for r in aq]
    pm25 = [r.pm25 for r in aq]
    drivers = {
        "wind_speed_mps": [getattr(wx.get(r.observed_at), "wind_speed_mps", None) for r in aq],
        "temperature_c": [getattr(wx.get(r.observed_at), "temperature_c", None) for r in aq],
        "humidity_pct": [getattr(wx.get(r.observed_at), "humidity_pct", None) for r in aq],
        "pressure_hpa": [getattr(wx.get(r.observed_at), "pressure_hpa", None) for r in aq],
        "ventilation_index": [getattr(wx.get(r.observed_at), "ventilation_index", None) for r in aq],
        "congestion_index": [getattr(tr.get(r.observed_at), "congestion_index", None) for r in aq],
    }
    return {
        "station": assembly.station_out(station).model_dump(),
        "window_hours": hours, "sample_size": len(aq),
        "correlations": [
            {"driver": name,
             "vs_aqi": _pearson(aqi, values),
             "vs_pm25": _pearson(pm25, values),
             "interpretation": _interpret(name, _pearson(aqi, values))}
            for name, values in drivers.items()],
        "note": "Pearson correlation over the selected window. Correlation is not "
                "causation — wind and traffic co-vary with time of day.",
    }


def _interpret(driver: str, r: float | None) -> str:
    if r is None:
        return "Not enough overlapping data in this window."
    strength = ("strong" if abs(r) > 0.6 else
                "moderate" if abs(r) > 0.35 else
                "weak" if abs(r) > 0.15 else "negligible")
    direction = "negative" if r < 0 else "positive"
    hints = {
        "wind_speed_mps": "Wind disperses pollutants, so a negative relationship "
                          "is expected.",
        "ventilation_index": "Higher ventilation means better mixing and lower "
                             "concentrations.",
        "congestion_index": "Congestion tracks tailpipe emissions and the "
                            "commuting cycle.",
        "humidity_pct": "High humidity aids secondary particle formation and "
                        "often accompanies stagnant nights.",
        "pressure_hpa": "High pressure accompanies subsidence and shallow mixing.",
        "temperature_c": "Temperature tracks the daily mixing cycle more than "
                         "emissions.",
    }
    return f"{strength.capitalize()} {direction} relationship. {hints.get(driver, '')}".strip()


@router.get("/compare")
def compare(city: str | None = None, station_id: int | None = None,
            mode: str = Query(default="day", pattern="^(day|week|month)$"),
            db: Session = Depends(get_db)) -> dict:
    """Today vs yesterday, this week vs last, this month vs last."""
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    now = datetime.now(timezone.utc)
    span = {"day": timedelta(days=1), "week": timedelta(days=7),
            "month": timedelta(days=30)}[mode]

    current = repository.range_series(db, station.id, now - span, now)
    previous = repository.range_series(db, station.id, now - 2 * span, now - span)

    def stats(rows) -> dict:
        aqi = [r.aqi for r in rows if r.aqi is not None]
        return {"count": len(rows), "average_aqi": mean(aqi),
                "max_aqi": max(aqi) if aqi else None,
                "min_aqi": min(aqi) if aqi else None,
                "average_pm25": mean([r.pm25 for r in rows]),
                "average_pm10": mean([r.pm10 for r in rows])}

    cur, prev = stats(current), stats(previous)
    change = None
    if cur["average_aqi"] and prev["average_aqi"]:
        change = round((cur["average_aqi"] - prev["average_aqi"])
                       / prev["average_aqi"] * 100, 1)
    return {"station": assembly.station_out(station).model_dump(), "mode": mode,
            "current": cur, "previous": prev, "change_pct": change,
            "verdict": ("worse than the previous period" if (change or 0) > 2 else
                        "better than the previous period" if (change or 0) < -2 else
                        "broadly unchanged")}


@router.get("/hourly-profile")
def hourly_profile(city: str | None = None, station_id: int | None = None,
                   days: int = Query(default=30, ge=3, le=120),
                   db: Session = Depends(get_db)) -> dict:
    """Average AQI by local hour — the shape officials use to time interventions."""
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    rows = repository.air_quality_series(db, station.id, hours=days * 24)
    ist = timezone(timedelta(hours=5, minutes=30))

    buckets: dict[int, list[float]] = {h: [] for h in range(24)}
    weekday: dict[int, list[float]] = {d: [] for d in range(7)}
    for row in rows:
        if row.aqi is None:
            continue
        local = row.observed_at.astimezone(ist)
        buckets[local.hour].append(row.aqi)
        weekday[local.weekday()].append(row.aqi)

    return {
        "station": assembly.station_out(station).model_dump(), "days": days,
        "by_hour": [{"hour": h, "average_aqi": mean(v), "samples": len(v)}
                    for h, v in buckets.items()],
        "by_weekday": [{"weekday": d, "label": ["Mon", "Tue", "Wed", "Thu", "Fri",
                                                 "Sat", "Sun"][d],
                        "average_aqi": mean(v), "samples": len(v)}
                       for d, v in weekday.items()],
        "note": "Local time (Asia/Kolkata).",
    }


@router.get("/station-ranking")
def station_ranking(city: str | None = None,
                    hours: int = Query(default=24, ge=1, le=24 * 30),
                    db: Session = Depends(get_db)) -> dict:
    resolved = resolve_city(db, city)
    out = []
    for station in repository.city_stations(db, resolved.id):
        rows = repository.air_quality_series(db, station.id, hours=hours)
        aqi = [r.aqi for r in rows if r.aqi is not None]
        if not aqi:
            continue
        out.append({"station": assembly.station_out(station).model_dump(),
                    "average_aqi": mean(aqi), "max_aqi": max(aqi),
                    "average_pm25": mean([r.pm25 for r in rows]),
                    "population_exposed": station.population_exposed,
                    "zone_type": station.zone_type.value})
    out.sort(key=lambda s: s["average_aqi"] or 0, reverse=True)
    return {"city": resolved.slug, "window_hours": hours, "stations": out}
