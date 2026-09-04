from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.common import ensure_city_fresh, ensure_fresh, resolve_city, resolve_station
from app.db.session import get_db
from app.domain.aqi import mean
from app.schemas.air import (CitySummary, CurrentAirQuality, HistoryResponse,
                              MapPoint, MapResponse, SeriesPoint)
from app.schemas.common import DataKind
from app.services import alerts as alert_service
from app.services import assembly, repository

router = APIRouter(prefix="/air-quality", tags=["air quality"])


@router.get("/cities")
def cities(db: Session = Depends(get_db)) -> list[dict]:
    out = []
    for city in repository.list_cities(db):
        stations = repository.city_stations(db, city.id)
        out.append(assembly.city_out(city, len(stations)).model_dump())
    return out


@router.get("/stations")
def stations(city: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    resolved = resolve_city(db, city)
    return [assembly.station_out(s).model_dump()
            for s in repository.city_stations(db, resolved.id)]


@router.get("/current", response_model=CurrentAirQuality)
def current(city: str | None = None, station_id: int | None = None,
            db: Session = Depends(get_db)) -> CurrentAirQuality:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    ensure_fresh(db, resolved_city, station)
    return assembly.current_air_quality(db, resolved_city, station)


@router.get("/summary", response_model=CitySummary)
def summary(city: str | None = None, db: Session = Depends(get_db)) -> CitySummary:
    resolved = resolve_city(db, city)
    ensure_city_fresh(db, resolved)
    stations = repository.city_stations(db, resolved.id)
    readings = repository.city_latest_readings(db, resolved.id)

    valid = [(s, readings[s.id]) for s in stations
             if s.id in readings and readings[s.id].aqi is not None]
    if not valid:
        return CitySummary(
            city=assembly.city_out(resolved, len(stations)), average_aqi=None,
            worst_station=None, worst_aqi=None, best_station=None, best_aqi=None,
            category=None, dominant_pollutant=None, station_count=len(stations),
            reporting_stations=0, hotspot_station_ids=[], updated_at=None,
            provenance=assembly.provenance_for(None))

    worst = max(valid, key=lambda pair: pair[1].aqi)
    best = min(valid, key=lambda pair: pair[1].aqi)
    average = mean([r.aqi for _, r in valid])
    dominant_counts: dict[str, int] = {}
    for _, r in valid:
        if r.dominant_pollutant:
            dominant_counts[r.dominant_pollutant] = dominant_counts.get(
                r.dominant_pollutant, 0) + 1
    dominant = max(dominant_counts, key=dominant_counts.get) if dominant_counts else None

    return CitySummary(
        city=assembly.city_out(resolved, len(stations)),
        average_aqi=average,
        worst_station=assembly.station_out(worst[0]), worst_aqi=worst[1].aqi,
        best_station=assembly.station_out(best[0]), best_aqi=best[1].aqi,
        category=assembly.category_out(average),
        dominant_pollutant=dominant, station_count=len(stations),
        reporting_stations=len(valid),
        hotspot_station_ids=alert_service.detect_hotspots(readings, stations),
        updated_at=max(r.observed_at for _, r in valid),
        provenance=assembly.provenance_for(worst[1]))


@router.get("/map", response_model=MapResponse)
def air_quality_map(city: str | None = None,
                    db: Session = Depends(get_db)) -> MapResponse:
    resolved = resolve_city(db, city)
    ensure_city_fresh(db, resolved)
    stations = repository.city_stations(db, resolved.id)
    readings = repository.city_latest_readings(db, resolved.id)
    hotspots = set(alert_service.detect_hotspots(readings, stations))

    points = []
    newest = None
    for station in stations:
        reading = readings.get(station.id)
        if reading and (newest is None or reading.observed_at > newest.observed_at):
            newest = reading
        points.append(MapPoint(
            station=assembly.station_out(station),
            aqi=reading.aqi if reading else None,
            category=assembly.category_out(reading.aqi) if reading else None,
            dominant_pollutant=reading.dominant_pollutant if reading else None,
            pm25=reading.pm25 if reading else None,
            pm10=reading.pm10 if reading else None,
            observed_at=reading.observed_at if reading else None,
            is_hotspot=station.id in hotspots))

    return MapResponse(city=assembly.city_out(resolved, len(stations)),
                       points=points, legend=assembly.legend(),
                       provenance=assembly.provenance_for(newest))


@router.get("/history", response_model=HistoryResponse)
def history(station_id: int | None = None, city: str | None = None,
            hours: int = Query(default=72, ge=1, le=24 * 90),
            start: datetime | None = None, end: datetime | None = None,
            db: Session = Depends(get_db)) -> HistoryResponse:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)

    if start and end:
        rows = repository.range_series(db, station.id, start, end)
        weather_rows = repository.weather_series(
            db, station.id, hours=int((end - start).total_seconds() // 3600) + 1, end=end)
        traffic_rows = repository.traffic_series(
            db, station.id, hours=int((end - start).total_seconds() // 3600) + 1, end=end)
    else:
        rows = repository.air_quality_series(db, station.id, hours=hours)
        weather_rows = repository.weather_series(db, station.id, hours=hours)
        traffic_rows = repository.traffic_series(db, station.id, hours=hours)

    weather_by_time = {w.observed_at: w for w in weather_rows}
    traffic_by_time = {t.observed_at: t for t in traffic_rows}

    points = []
    for row in rows:
        w = weather_by_time.get(row.observed_at)
        t = traffic_by_time.get(row.observed_at)
        points.append(SeriesPoint(
            at=row.observed_at, aqi=row.aqi, pm25=row.pm25, pm10=row.pm10,
            no2=row.no2, so2=row.so2, co=row.co, o3=row.o3,
            temperature_c=getattr(w, "temperature_c", None),
            humidity_pct=getattr(w, "humidity_pct", None),
            wind_speed_mps=getattr(w, "wind_speed_mps", None),
            congestion_index=getattr(t, "congestion_index", None)))

    aqis = [p.aqi for p in points if p.aqi is not None]
    peak = max(points, key=lambda p: p.aqi or -1) if aqis else None
    cleanest = min((p for p in points if p.aqi is not None),
                   key=lambda p: p.aqi, default=None)
    stats = {
        "count": len(points),
        "average_aqi": mean(aqis),
        "max_aqi": max(aqis) if aqis else None,
        "min_aqi": min(aqis) if aqis else None,
        "peak_at": peak.at if peak else None,
        "cleanest_at": cleanest.at if cleanest else None,
        "average_pm25": mean([p.pm25 for p in points]),
        "average_pm10": mean([p.pm10 for p in points]),
    }
    return HistoryResponse(station=assembly.station_out(station), points=points,
                           stats=stats,
                           provenance=assembly.provenance_for(rows[-1] if rows else None))
