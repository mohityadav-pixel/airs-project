from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.context import build_station_context
from app.ai.explain import explain_forecast
from app.api.v1.common import ensure_fresh, resolve_city, resolve_station
from app.db.models import Prediction
from app.db.session import get_db
from app.schemas.air import ExplanationOut, ForecastPoint, PredictionResponse
from app.schemas.common import DataKind, DataProvenance, SourceMode
from app.services import assembly, repository
from app.services.source_attribution import estimate_sources
from ml.predict import forecast_station, hourly_curve

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _point(fc) -> ForecastPoint:
    return ForecastPoint(target_at=fc.target_at, horizon_hours=fc.horizon_hours,
                         aqi=fc.aqi, aqi_lower=fc.aqi_lower, aqi_upper=fc.aqi_upper,
                         pm25=fc.pm25, pm10=fc.pm10, confidence=fc.confidence,
                         risk_category=fc.risk_category, tier=fc.tier)


@router.get("", response_model=PredictionResponse)
def predictions(city: str | None = None, station_id: int | None = None,
                curve_hours: int = Query(default=24, ge=6, le=72),
                explain: bool = True, persist: bool = False,
                db: Session = Depends(get_db)) -> PredictionResponse:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    ensure_fresh(db, resolved_city, station)

    horizons, meta = forecast_station(db, station)
    curve = hourly_curve(db, station, hours=curve_hours)

    reading = repository.latest_air_quality(db, station.id)
    weather = repository.latest_weather(db, station.id)
    traffic = repository.latest_traffic(db, station.id)
    current_aqi = reading.aqi if reading else None

    source_estimate = None
    if reading:
        source_estimate = estimate_sources(
            pm25=reading.pm25, pm10=reading.pm10, no2=reading.no2,
            so2=reading.so2, co=reading.co, o3=reading.o3,
            wind_speed_mps=getattr(weather, "wind_speed_mps", None),
            ventilation_index=getattr(weather, "ventilation_index", None),
            congestion_index=getattr(traffic, "congestion_index", None),
            observed_at=reading.observed_at, zone=station.zone_type.value,
            near_road=station.near_major_road,
            near_industrial=station.near_industrial,
            near_construction=station.near_construction)

    peak = max(curve, key=lambda p: p.aqi or -1) if curve else None
    trough = min((p for p in curve if p.aqi is not None),
                 key=lambda p: p.aqi, default=None)

    explanation = None
    if explain and horizons:
        context = build_station_context(db, resolved_city, station,
                                        forecasts=horizons,
                                        source_estimate=source_estimate)
        result = explain_forecast(
            current_aqi=current_aqi,
            forecast=next((h for h in horizons if h.horizon_hours == 24), horizons[0]),
            weather=weather, source_estimate=source_estimate,
            station_name=station.name, facts=context["facts"])
        explanation = ExplanationOut(**{k: result[k] for k in
                                        ("headline", "simple", "technical",
                                         "factors", "tier")})

    if persist and horizons:
        now = datetime.now(timezone.utc)
        for fc in horizons:
            db.add(Prediction(
                station_id=station.id, issued_at=now, target_at=fc.target_at,
                horizon_hours=fc.horizon_hours, model_name=meta["model_name"],
                model_version=meta["model_version"], predicted_aqi=fc.aqi,
                predicted_pm25=fc.pm25, predicted_pm10=fc.pm10,
                aqi_lower=fc.aqi_lower, aqi_upper=fc.aqi_upper,
                confidence=fc.confidence, risk_category=fc.risk_category,
                drivers=fc.drivers))
        db.commit()

    return PredictionResponse(
        station=assembly.station_out(station),
        issued_at=meta.get("issued_at"), current_aqi=current_aqi,
        horizons=[_point(h) for h in horizons],
        curve=[_point(c) for c in curve],
        peak=_point(peak) if peak else None,
        trough=_point(trough) if trough else None,
        model=meta,
        explanation=explanation,
        provenance=DataProvenance(
            kind=DataKind.predicted,
            mode=SourceMode.demo if (reading and reading.provenance.value == "demo")
            else SourceMode.live,
            source=f"{meta['model_name']} {meta['model_version']} ({meta['tier']} tier)",
            generated_at=datetime.now(timezone.utc),
            note="Machine-learning forecast with an 80% prediction interval. "
                 "Not a measurement."))
