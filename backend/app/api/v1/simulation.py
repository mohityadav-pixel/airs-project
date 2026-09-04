from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.api.v1.common import ensure_fresh, resolve_city, resolve_station
from app.api.v1.sources import estimate_for_station
from app.core.errors import DataUnavailable, InvalidRequest
from app.db.models import Intervention, Simulation, User
from app.db.session import get_db
from app.schemas.action import InterventionOut, SimulationRequest, SimulationResponse
from app.schemas.common import DataKind, DataProvenance, SourceMode
from app.services import assembly, repository
from app.services.simulation import LeverInput, simulate

router = APIRouter(prefix="/simulation", tags=["what-if simulator"])


# Presentation order: the levers a city reaches for first, not alphabetical.
DISPLAY_ORDER = ["traffic_reduction", "road_dust_suppression",
                 "construction_halt", "industrial_emission_control",
                 "biomass_burning_control", "public_transport_boost"]


@router.get("/interventions", response_model=list[InterventionOut])
def interventions(db: Session = Depends(get_db)) -> list[Intervention]:
    rows = list(db.scalars(select(Intervention)))
    rows.sort(key=lambda i: (DISPLAY_ORDER.index(i.key)
                             if i.key in DISPLAY_ORDER else len(DISPLAY_ORDER),
                             i.label))
    return rows


@router.post("", response_model=SimulationResponse)
def run_simulation(payload: SimulationRequest, db: Session = Depends(get_db),
                   user: User | None = Depends(get_current_user_optional)
                   ) -> SimulationResponse:
    city = resolve_city(db, payload.city_slug)
    station = resolve_station(db, city, payload.station_id)
    ensure_fresh(db, city, station)

    reading = repository.latest_air_quality(db, station.id)
    if reading is None:
        raise DataUnavailable("No current reading at this station to simulate from.")
    weather = repository.latest_weather(db, station.id)
    estimate, _, _ = estimate_for_station(db, station)
    if estimate is None:
        raise DataUnavailable("Source attribution unavailable for this station.")

    catalogue = {i.key: i for i in db.scalars(select(Intervention))}
    levers: list[LeverInput] = []
    for lever in payload.levers:
        meta = catalogue.get(lever.key)
        if meta is None:
            raise InvalidRequest(f"Unknown intervention '{lever.key}'.")
        levers.append(LeverInput(key=meta.key, magnitude=lever.magnitude,
                                 effectiveness=meta.effectiveness, label=meta.label,
                                 max_magnitude=meta.max_magnitude))

    result = simulate(
        concentrations={"pm25": reading.pm25, "pm10": reading.pm10,
                        "no2": reading.no2, "so2": reading.so2,
                        "co": reading.co, "o3": reading.o3},
        source_shares=estimate.contributions, levers=levers,
        wind_speed_mps=getattr(weather, "wind_speed_mps", None),
        ventilation_index=getattr(weather, "ventilation_index", None),
        population_exposed=station.population_exposed)

    if payload.save:
        db.add(Simulation(
            user_id=user.id if user else None, city_id=city.id,
            station_id=station.id, name=payload.name,
            levers={l.key: l.magnitude for l in payload.levers},
            baseline=result.baseline, result={"simulated": result.simulated,
                                              "deltas": result.deltas},
            engine_version=result.engine_version))
        db.commit()

    return SimulationResponse(
        station=assembly.station_out(station), baseline=result.baseline,
        simulated=result.simulated, deltas=result.deltas,
        per_lever=result.per_lever, assumptions=result.assumptions,
        warnings=result.warnings, confidence=result.confidence,
        engine_version=result.engine_version, caveat=result.caveat,
        provenance=DataProvenance(
            kind=DataKind.simulated,
            mode=SourceMode.demo if reading.provenance.value == "demo" else SourceMode.live,
            source=f"AIRS simulation engine {result.engine_version}",
            observed_at=reading.observed_at,
            generated_at=datetime.now(timezone.utc), note=result.caveat))


@router.get("/history")
def simulation_history(limit: int = 20, db: Session = Depends(get_db),
                       user: User | None = Depends(get_current_user_optional)) -> list[dict]:
    if user is None:
        return []
    rows = db.scalars(select(Simulation).where(Simulation.user_id == user.id)
                      .order_by(Simulation.created_at.desc()).limit(limit))
    return [{"id": s.id, "name": s.name, "levers": s.levers,
             "baseline_aqi": s.baseline.get("aqi"),
             "simulated_aqi": s.result.get("simulated", {}).get("aqi"),
             "created_at": s.created_at} for s in rows]
