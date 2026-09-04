from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.common import ensure_fresh, resolve_city, resolve_station
from app.core.errors import DataUnavailable
from app.db.models import PollutionSourceEstimate
from app.db.session import get_db
from app.schemas.air import SourceContribution, SourceResponse
from app.schemas.common import DataKind, DataProvenance, SourceMode
from app.services import assembly, repository
from app.services.source_attribution import SOURCE_LABELS, estimate_sources

router = APIRouter(prefix="/pollution-sources", tags=["pollution sources"])


def estimate_for_station(db: Session, station):
    reading = repository.latest_air_quality(db, station.id)
    if reading is None:
        return None, None, None
    weather = repository.latest_weather(db, station.id)
    traffic = repository.latest_traffic(db, station.id)
    estimate = estimate_sources(
        pm25=reading.pm25, pm10=reading.pm10, no2=reading.no2, so2=reading.so2,
        co=reading.co, o3=reading.o3,
        wind_speed_mps=getattr(weather, "wind_speed_mps", None),
        ventilation_index=getattr(weather, "ventilation_index", None),
        congestion_index=getattr(traffic, "congestion_index", None),
        observed_at=reading.observed_at, zone=station.zone_type.value,
        near_road=station.near_major_road,
        near_industrial=station.near_industrial,
        near_construction=station.near_construction)
    return estimate, reading, weather


@router.get("", response_model=SourceResponse)
def sources(city: str | None = None, station_id: int | None = None,
            persist: bool = False, db: Session = Depends(get_db)) -> SourceResponse:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    ensure_fresh(db, resolved_city, station)

    estimate, reading, _ = estimate_for_station(db, station)
    if estimate is None:
        raise DataUnavailable("No current reading at this station, so sources "
                              "cannot be attributed.")

    if persist:
        db.add(PollutionSourceEstimate(
            station_id=station.id, estimated_at=datetime.now(timezone.utc),
            method=estimate.method, contributions=estimate.contributions,
            evidence=estimate.evidence, confidence=estimate.confidence))
        db.commit()

    contributions = [
        SourceContribution(key=k, label=SOURCE_LABELS[k], share_pct=v)
        for k, v in sorted(estimate.contributions.items(),
                           key=lambda kv: kv[1], reverse=True)]

    return SourceResponse(
        station=assembly.station_out(station), contributions=contributions,
        evidence=estimate.evidence, confidence=estimate.confidence,
        method=estimate.method,
        provenance=DataProvenance(
            kind=DataKind.estimated,
            mode=SourceMode.demo if reading.provenance.value == "demo" else SourceMode.live,
            source="AIRS source-attribution heuristic",
            observed_at=reading.observed_at,
            generated_at=datetime.now(timezone.utc),
            note="Model-based estimate from pollutant ratios, meteorology and "
                 "site context. Not a chemical speciation measurement."))
