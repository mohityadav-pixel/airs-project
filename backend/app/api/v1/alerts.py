from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.common import ensure_city_fresh, resolve_city
from app.api.v1.sources import estimate_for_station
from app.db.session import get_db
from app.schemas.action import AlertOut
from app.services import alerts as alert_service
from app.services import repository
from ml.predict import forecast_station

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def alerts(city: str | None = None, evaluate: bool = True,
           db: Session = Depends(get_db)) -> list[AlertOut]:
    resolved = resolve_city(db, city)
    if evaluate:
        ensure_city_fresh(db, resolved)
        alert_service.deactivate_expired(db)
        readings = repository.city_latest_readings(db, resolved.id)
        for station in repository.city_stations(db, resolved.id):
            reading = readings.get(station.id)
            if reading is None:
                continue
            horizons, _ = forecast_station(db, station, horizons=(6, 24))
            peak = max((h.aqi for h in horizons if h.aqi is not None), default=None)
            hours = next((h.horizon_hours for h in horizons if h.aqi == peak), None)
            estimate, _, _ = estimate_for_station(db, station)
            alert_service.evaluate_station(
                db, resolved, station, reading=reading, forecast_peak=peak,
                hours_to_peak=hours,
                source_shares=estimate.contributions if estimate else None)
        db.commit()

    out = []
    for alert in repository.active_alerts(db, resolved.id):
        out.append(AlertOut(
            id=alert.id, kind=alert.kind, severity=alert.severity.value,
            title=alert.title, what_happened=alert.what_happened,
            why_it_matters=alert.why_it_matters,
            recommended_action=alert.recommended_action,
            expected_duration_hours=alert.expected_duration_hours,
            raised_at=alert.raised_at, expires_at=alert.expires_at,
            station_id=alert.station_id,
            station_name=alert.station.name if alert.station else None,
            context=alert.context))
    return out
