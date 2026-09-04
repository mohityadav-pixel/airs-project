from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.air import StationOut
from app.schemas.common import DataProvenance


class InterventionOut(BaseModel):
    key: str
    label: str
    category: str
    description: str
    unit: str
    max_magnitude: float
    lag_hours: int
    cost_band: str
    evidence_note: str | None = None
    effectiveness: dict


class LeverRequest(BaseModel):
    key: str
    magnitude: float = Field(ge=0, le=100)


class SimulationRequest(BaseModel):
    station_id: int | None = None
    city_slug: str | None = None
    levers: list[LeverRequest] = Field(min_length=1, max_length=6)
    name: str | None = None
    save: bool = False


class SimulationResponse(BaseModel):
    station: StationOut | None
    baseline: dict
    simulated: dict
    deltas: dict
    per_lever: list[dict]
    assumptions: list[str]
    warnings: list[str]
    confidence: float
    engine_version: str
    caveat: str
    provenance: DataProvenance


class RecommendationOut(BaseModel):
    action: str
    reason: str
    expected_impact: str
    intervention_key: str | None
    time_horizon: str
    priority_score: float
    priority_factors: dict
    confidence: float
    station_id: int | None
    station_name: str | None
    modelled_improvement_pct: float | None
    briefing: str | None = None


class RecommendationResponse(BaseModel):
    city_slug: str
    generated_at: datetime
    immediate: list[RecommendationOut]
    short_term: list[RecommendationOut]
    long_term: list[RecommendationOut]
    methodology: dict
    provenance: DataProvenance


class AlertOut(BaseModel):
    id: int
    kind: str
    severity: str
    title: str
    what_happened: str
    why_it_matters: str
    recommended_action: str
    expected_duration_hours: int | None
    raised_at: datetime
    expires_at: datetime | None
    station_id: int | None
    station_name: str | None
    context: dict | None


class HealthRequest(BaseModel):
    station_id: int | None = None
    city_slug: str | None = None
    group: str = "general"


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    city_slug: str | None = None
    station_id: int | None = None
    conversation_id: int | None = None


class CopilotResponse(BaseModel):
    answer: str
    grounding: dict
    conversation_id: int | None
    generated_at: datetime
    suggested_questions: list[str]
    provenance: DataProvenance
