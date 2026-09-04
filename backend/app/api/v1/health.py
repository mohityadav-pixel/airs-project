from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.api.v1.common import ensure_fresh, resolve_city, resolve_station
from app.core.errors import InvalidRequest
from app.db.models import SensitivityGroup, User
from app.db.session import get_db
from app.services import repository
from app.services.health import GROUP_LABEL, advisory

router = APIRouter(prefix="/health-advisory", tags=["health"])


@router.get("/groups")
def groups() -> list[dict]:
    return [{"key": g.value, "label": GROUP_LABEL[g]} for g in SensitivityGroup]


@router.get("")
def health_advisory(city: str | None = None, station_id: int | None = None,
                    group: str | None = None, db: Session = Depends(get_db),
                    user: User | None = Depends(get_current_user_optional)) -> dict:
    resolved_city = resolve_city(db, city)
    station = resolve_station(db, resolved_city, station_id)
    ensure_fresh(db, resolved_city, station)

    if group:
        try:
            sensitivity = SensitivityGroup(group)
        except ValueError:
            raise InvalidRequest(f"Unknown group '{group}'.")
    elif user is not None:
        sensitivity = user.sensitivity_group
    else:
        sensitivity = SensitivityGroup.general

    reading = repository.latest_air_quality(db, station.id)
    result = advisory(reading.aqi if reading else None, sensitivity,
                      dominant_pollutant=reading.dominant_pollutant if reading else None)
    result["station"] = {"id": station.id, "name": station.name}
    result["observed_at"] = reading.observed_at if reading else None
    result["provenance"] = {"kind": "estimated",
                            "mode": reading.provenance.value if reading else "live",
                            "source": "AIRS health guidance (US EPA cautionary "
                                      "statements, adjusted by group)"}
    return result
