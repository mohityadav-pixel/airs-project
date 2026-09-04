"""City Command Center — the official-facing consolidated view.

One request returns everything an operations desk needs, so the dashboard does
not fan out into a dozen calls and drift out of sync between panels.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.api.v1.common import ensure_city_fresh, resolve_city
from app.api.v1.sources import estimate_for_station
from app.db.models import Intervention, Role, User
from app.db.session import get_db
from app.domain.aqi import mean
from app.services import alerts as alert_service
from app.services import assembly, repository
from app.services.priority import compute_priority
from app.services.simulation import LeverInput, simulate
from app.services.source_attribution import SOURCE_LABELS
from ml.predict import forecast_station

router = APIRouter(prefix="/command-center", tags=["command center"])


@router.get("")
def command_center(city: str | None = None, db: Session = Depends(get_db),
                   user: User = Depends(require_role(Role.official))) -> dict:
    resolved = resolve_city(db, city)
    ensure_city_fresh(db, resolved)
    stations = repository.city_stations(db, resolved.id)
    readings = repository.city_latest_readings(db, resolved.id)
    hotspots = set(alert_service.detect_hotspots(readings, stations))
    catalogue = {i.key: i for i in db.scalars(select(Intervention))}
    max_population = max([s.population_exposed or 0 for s in stations] + [1])

    zones = []
    for station in stations:
        reading = readings.get(station.id)
        if reading is None:
            continue
        horizons, _ = forecast_station(db, station, horizons=(6, 24))
        predicted = max((h.aqi for h in horizons if h.aqi is not None), default=None)
        hours_to_peak = next((h.horizon_hours for h in horizons
                              if h.aqi == predicted), None)
        estimate, _, weather = estimate_for_station(db, station)
        top_source = (max(estimate.contributions, key=estimate.contributions.get)
                      if estimate else None)

        # Best available lever here, modelled at 30%.
        best_improvement = None
        best_lever = None
        if estimate:
            for key, meta in catalogue.items():
                result = simulate(
                    concentrations={"pm25": reading.pm25, "pm10": reading.pm10,
                                    "no2": reading.no2, "so2": reading.so2,
                                    "co": reading.co, "o3": reading.o3},
                    source_shares=estimate.contributions,
                    levers=[LeverInput(key=key, magnitude=30.0,
                                       effectiveness=meta.effectiveness,
                                       label=meta.label,
                                       max_magnitude=meta.max_magnitude)],
                    wind_speed_mps=getattr(weather, "wind_speed_mps", None),
                    ventilation_index=getattr(weather, "ventilation_index", None))
                improvement = result.deltas.get("improvement_pct") or 0
                if best_improvement is None or improvement > best_improvement:
                    best_improvement, best_lever = improvement, meta.label

        priority = compute_priority(
            current_aqi=reading.aqi, predicted_aqi=predicted,
            population_exposed=station.population_exposed,
            modelled_improvement_pct=best_improvement,
            hours_until_peak=hours_to_peak, max_population=max_population)

        zones.append({
            "station": assembly.station_out(station).model_dump(),
            "aqi": reading.aqi,
            "category": (assembly.category_out(reading.aqi).model_dump()
                         if reading.aqi is not None else None),
            "pm25": reading.pm25, "pm10": reading.pm10,
            "observed_at": reading.observed_at,
            "is_hotspot": station.id in hotspots,
            "predicted_peak_aqi": predicted,
            "hours_to_peak": hours_to_peak,
            "expected_change": (round(predicted - reading.aqi, 1)
                                if predicted is not None and reading.aqi is not None
                                else None),
            "top_source": top_source,
            "top_source_label": SOURCE_LABELS.get(top_source) if top_source else None,
            "source_confidence": estimate.confidence if estimate else None,
            "best_lever": best_lever,
            "best_lever_improvement_pct": best_improvement,
            "priority_score": priority.score,
            "priority_factors": priority.factors,
            "priority_rationale": priority.rationale,
        })

    zones.sort(key=lambda z: z["priority_score"], reverse=True)
    aqis = [z["aqi"] for z in zones if z["aqi"] is not None]
    deteriorating = [z for z in zones
                     if (z["expected_change"] or 0) >= 15]

    active_alerts = repository.active_alerts(db, resolved.id)
    return {
        "city": assembly.city_out(resolved, len(stations)).model_dump(),
        "generated_at": datetime.now(timezone.utc),
        "headline": {
            "average_aqi": mean(aqis),
            "worst_aqi": max(aqis) if aqis else None,
            "stations_reporting": len(zones),
            "stations_total": len(stations),
            "hotspot_count": len(hotspots),
            "deteriorating_count": len(deteriorating),
            "active_alerts": len(active_alerts),
            "population_in_hotspots": sum(
                z["station"]["population_exposed"] or 0 for z in zones
                if z["is_hotspot"]),
        },
        "zones": zones,
        "deteriorating": deteriorating[:5],
        "alerts": [{"id": a.id, "severity": a.severity.value, "title": a.title,
                    "what_happened": a.what_happened,
                    "why_it_matters": a.why_it_matters,
                    "recommended_action": a.recommended_action,
                    "station_name": a.station.name if a.station else None,
                    "raised_at": a.raised_at} for a in active_alerts[:12]],
        "methodology": {
            "priority": "Weighted geometric mean of severity, exposure, predicted "
                        "risk, modelled intervention impact and urgency.",
            "hotspot": "A station at or above 1.25x the city median AQI — relative, "
                       "so it works in both a clean city and a polluted one.",
            "best_lever": "The intervention with the largest modelled AQI benefit "
                          "at a 30% magnitude, given this station's estimated "
                          "source mix.",
        },
    }
