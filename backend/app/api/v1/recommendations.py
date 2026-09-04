from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.common import ensure_city_fresh, resolve_city
from app.api.v1.sources import estimate_for_station
from app.db.models import Intervention
from app.db.session import get_db
from app.schemas.action import RecommendationOut, RecommendationResponse
from app.schemas.common import DataKind, DataProvenance, SourceMode
from app.services import repository
from app.services.recommendations import long_term_actions, recommend_for_station
from ml.predict import forecast_station

router = APIRouter(prefix="/recommendations", tags=["city actions"])

METHODOLOGY = {
    "selection": "Actions are chosen by rule from the estimated dominant source "
                 "at each station, not by a language model.",
    "impact": "Expected impact is produced by the AIRS simulation engine at a "
              "realistic 30% intervention magnitude, applied only to the share "
              "of each pollutant attributed to that source.",
    "priority": "Priority = weighted geometric mean of pollution severity, "
                "population exposure, predicted risk, modelled intervention "
                "impact and urgency. Every factor is returned with the score.",
    "limits": "Source shares are estimates, and per-source effectiveness figures are planning "
              "figures. Treat rankings as decision support, not as certainty.",
}


@router.get("", response_model=RecommendationResponse)
def recommendations(city: str | None = None, limit_per_horizon: int = 6,
                    db: Session = Depends(get_db)) -> RecommendationResponse:
    resolved = resolve_city(db, city)
    ensure_city_fresh(db, resolved)
    stations = repository.city_stations(db, resolved.id)
    readings = repository.city_latest_readings(db, resolved.id)
    catalogue = {i.key: {"label": i.label, "effectiveness": i.effectiveness,
                         "max_magnitude": i.max_magnitude}
                 for i in db.scalars(select(Intervention))}
    max_population = max([s.population_exposed or 0 for s in stations] + [1])

    generated: list = []
    dominant_sources: set[str] = set()

    # Focus effort where it matters: the worst-reporting stations in the city.
    ranked = sorted((s for s in stations if s.id in readings),
                    key=lambda s: readings[s.id].aqi or 0, reverse=True)[:5]

    for station in ranked:
        reading = readings[station.id]
        estimate, _, weather = estimate_for_station(db, station)
        if estimate is None:
            continue
        dominant_sources.add(max(estimate.contributions,
                                 key=estimate.contributions.get))
        horizons, _ = forecast_station(db, station, horizons=(6, 24))
        predicted = max((h.aqi for h in horizons if h.aqi is not None), default=None)
        hours_to_peak = next((h.horizon_hours for h in horizons
                              if h.aqi == predicted), None)

        generated.extend(recommend_for_station(
            station=station, current_aqi=reading.aqi, predicted_aqi=predicted,
            concentrations={"pm25": reading.pm25, "pm10": reading.pm10,
                            "no2": reading.no2, "so2": reading.so2,
                            "co": reading.co, "o3": reading.o3},
            source_shares=estimate.contributions, interventions=catalogue,
            wind_speed_mps=getattr(weather, "wind_speed_mps", None),
            ventilation_index=getattr(weather, "ventilation_index", None),
            hours_until_peak=hours_to_peak, max_population=max_population))

    generated.sort(key=lambda r: r.priority_score, reverse=True)

    # Collapse the same lever repeated across stations into one action that
    # names the other affected zones, so the list reads as a plan rather than
    # as one row per station.
    deduped: list = []
    seen: dict[str, object] = {}
    for rec in generated:
        key = f"{rec.intervention_key}:{rec.time_horizon}"
        if key in seen:
            leader = seen[key]
            others = getattr(leader, "_also", [])
            if rec.station_name and rec.station_name not in others:
                others.append(rec.station_name)
                leader._also = others
            continue
        seen[key] = rec
        deduped.append(rec)

    for rec in deduped:
        also = getattr(rec, "_also", [])
        if also:
            rec.reason += (" The same lever is also the leading option at "
                           + ", ".join(also[:3])
                           + (f" and {len(also) - 3} more zones." if len(also) > 3
                              else "."))

    def bucket(horizon: str) -> list[RecommendationOut]:
        return [RecommendationOut(**asdict(r)) for r in deduped
                if r.time_horizon == horizon][:limit_per_horizon]

    newest = max((r.observed_at for r in readings.values()), default=None)
    any_demo = any(r.provenance.value == "demo" for r in readings.values())

    return RecommendationResponse(
        city_slug=resolved.slug, generated_at=datetime.now(timezone.utc),
        immediate=bucket("immediate"), short_term=bucket("short"),
        long_term=[RecommendationOut(**asdict(r))
                   for r in long_term_actions(sorted(dominant_sources))],
        methodology=METHODOLOGY,
        provenance=DataProvenance(
            kind=DataKind.estimated,
            mode=SourceMode.demo if any_demo else SourceMode.live,
            source="AIRS recommendation engine (rule-based) + simulation engine",
            observed_at=newest, generated_at=datetime.now(timezone.utc),
            note="Decision support derived from measured air quality, forecasts "
                 "and estimated source shares."))
