"""AIRS relational schema.

Design notes
------------
* Every measurement table stores *both* the observation timestamp and the
  ingestion timestamp, so staleness is a first-class, queryable property.
* ``provenance`` on measurement rows records where a value came from
  (``live`` / ``demo``) — the UI is never allowed to guess.
* Composite indexes are on ``(station_id, observed_at DESC)`` because that is
  the shape of essentially every read: "latest N readings for this station".
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (Boolean, Enum, Float, ForeignKey, Index, Integer,
                        JSON, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UtcDateTime


class Role(str, enum.Enum):
    citizen = "citizen"
    analyst = "analyst"
    official = "official"
    admin = "admin"


class Provenance(str, enum.Enum):
    live = "live"          # fetched from a real upstream provider
    demo = "demo"          # deterministic synthetic data, labelled in the UI
    derived = "derived"    # computed by AIRS from other stored rows


class SensitivityGroup(str, enum.Enum):
    general = "general"
    outdoor_worker = "outdoor_worker"
    athlete = "athlete"
    child = "child"
    elderly = "elderly"
    sensitive = "sensitive"


# ────────────────────────────── identity ──────────────────────────────

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.citizen,
                                       nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    home_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    sensitivity_group: Mapped[SensitivityGroup] = mapped_column(
        Enum(SensitivityGroup, native_enum=False), default=SensitivityGroup.general, nullable=False)

    home_city = relationship("City", lazy="joined")
    conversations = relationship("Conversation", back_populates="user",
                                 cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(String(120))
    outcome: Mapped[str] = mapped_column(String(24), default="success", nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON)


# ────────────────────────────── geography ─────────────────────────────

class City(Base, TimestampMixin):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(80), default="India", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    population: Mapped[int | None] = mapped_column(Integer)
    default_zoom: Mapped[int] = mapped_column(Integer, default=11, nullable=False)
    waqi_keyword: Mapped[str | None] = mapped_column(String(120))
    aqi_scale: Mapped[str] = mapped_column(String(16), default="us_epa", nullable=False)

    stations = relationship("Station", back_populates="city",
                            cascade="all, delete-orphan")


class ZoneType(str, enum.Enum):
    residential = "residential"
    commercial = "commercial"
    industrial = "industrial"
    traffic_corridor = "traffic_corridor"
    construction = "construction"
    green = "green"
    mixed = "mixed"


class Station(Base, TimestampMixin):
    """A monitoring location. ``zone_type`` and the context flags below are what
    make source apportionment possible — a station beside a freight corridor and
    one in a park interpret an identical PM2.5 reading very differently."""

    __tablename__ = "monitoring_stations"
    __table_args__ = (UniqueConstraint("city_id", "code", name="uq_station_city_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"),
                                         index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType, native_enum=False),
                                                default=ZoneType.mixed, nullable=False)
    population_exposed: Mapped[int | None] = mapped_column(Integer)
    near_major_road: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    near_industrial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    near_construction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(120))

    city = relationship("City", back_populates="stations")


# ──────────────────────────── measurements ────────────────────────────

class AirQualityReading(Base):
    __tablename__ = "air_quality_readings"
    __table_args__ = (
        UniqueConstraint("station_id", "observed_at", name="uq_aq_station_time"),
        Index("ix_aq_station_observed", "station_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="CASCADE"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime,
                                                  index=True, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    provenance: Mapped[Provenance] = mapped_column(Enum(Provenance, native_enum=False),
                                                   default=Provenance.live, nullable=False)

    aqi: Mapped[float | None] = mapped_column(Float)
    dominant_pollutant: Mapped[str | None] = mapped_column(String(16))
    # concentrations
    pm25: Mapped[float | None] = mapped_column(Float)
    pm10: Mapped[float | None] = mapped_column(Float)
    no2: Mapped[float | None] = mapped_column(Float)
    so2: Mapped[float | None] = mapped_column(Float)
    co: Mapped[float | None] = mapped_column(Float)
    o3: Mapped[float | None] = mapped_column(Float)
    # per-pollutant AQI sub-indices, kept so we never recompute lossily
    sub_indices: Mapped[dict | None] = mapped_column(JSON)
    quality_flags: Mapped[list | None] = mapped_column(JSON)

    station = relationship("Station")


class WeatherReading(Base):
    __tablename__ = "weather_readings"
    __table_args__ = (
        UniqueConstraint("station_id", "observed_at", name="uq_weather_station_time"),
        Index("ix_weather_station_observed", "station_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="CASCADE"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime,
                                                  index=True, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    provenance: Mapped[Provenance] = mapped_column(Enum(Provenance, native_enum=False),
                                                   default=Provenance.live, nullable=False)

    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_speed_mps: Mapped[float | None] = mapped_column(Float)
    wind_deg: Mapped[float | None] = mapped_column(Float)
    rain_1h_mm: Mapped[float | None] = mapped_column(Float)
    clouds_pct: Mapped[float | None] = mapped_column(Float)
    visibility_m: Mapped[float | None] = mapped_column(Float)
    condition: Mapped[str | None] = mapped_column(String(48))
    # Derived dispersion proxy: low values mean pollutants accumulate.
    ventilation_index: Mapped[float | None] = mapped_column(Float)


class TrafficReading(Base):
    __tablename__ = "traffic_readings"
    __table_args__ = (
        UniqueConstraint("station_id", "observed_at", name="uq_traffic_station_time"),
        Index("ix_traffic_station_observed", "station_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="CASCADE"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime,
                                                  index=True, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    provenance: Mapped[Provenance] = mapped_column(Enum(Provenance, native_enum=False),
                                                   default=Provenance.live, nullable=False)
    congestion_index: Mapped[float | None] = mapped_column(Float)   # 0..1
    speed_ratio: Mapped[float | None] = mapped_column(Float)        # current/free-flow
    vehicle_volume_est: Mapped[float | None] = mapped_column(Float)


# ───────────────────────────── intelligence ───────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_pred_station_target", "station_id", "target_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="CASCADE"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    target_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)

    predicted_aqi: Mapped[float | None] = mapped_column(Float)
    predicted_pm25: Mapped[float | None] = mapped_column(Float)
    predicted_pm10: Mapped[float | None] = mapped_column(Float)
    aqi_lower: Mapped[float | None] = mapped_column(Float)
    aqi_upper: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)   # 0..1
    risk_category: Mapped[str | None] = mapped_column(String(40))
    drivers: Mapped[list | None] = mapped_column(JSON)        # feature attributions


class PollutionSourceEstimate(Base):
    __tablename__ = "pollution_sources"
    __table_args__ = (Index("ix_source_station_time", "station_id", "estimated_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="CASCADE"), nullable=False)
    estimated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    method: Mapped[str] = mapped_column(String(60), nullable=False)
    contributions: Mapped[dict] = mapped_column(JSON, nullable=False)  # {source: share}
    evidence: Mapped[list | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)


class AlertSeverity(str, enum.Enum):
    info = "info"
    watch = "watch"
    warning = "warning"
    emergency = "emergency"


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_city_active", "city_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"),
                                         nullable=False)
    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_duration_hours: Mapped[int | None] = mapped_column(Integer)
    raised_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON)

    station = relationship("Station")


class Intervention(Base, TimestampMixin):
    """Catalogue of levers a city can actually pull. Coefficients live here (not
    in code) so they can be re-calibrated per city without a redeploy."""

    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="percent_reduction", nullable=False)
    max_magnitude: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    # For each pollutant, the fraction of THIS SOURCE's contribution that the
    # lever removes when applied at full magnitude (0..1). Kept separate from
    # the source share, which comes from live attribution — multiplying the two
    # is what makes the simulator physically sane.
    effectiveness: Mapped[dict] = mapped_column(JSON, nullable=False)
    lag_hours: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    cost_band: Mapped[str] = mapped_column(String(24), default="medium", nullable=False)
    evidence_note: Mapped[str | None] = mapped_column(Text)


class Simulation(Base, TimestampMixin):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"),
                                         nullable=False)
    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="SET NULL"))
    name: Mapped[str | None] = mapped_column(String(160))
    levers: Mapped[dict] = mapped_column(JSON, nullable=False)
    baseline: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_reco_city_horizon", "city_id", "time_horizon"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"),
                                         nullable=False)
    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_stations.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(240), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    intervention_key: Mapped[str | None] = mapped_column(String(64))
    time_horizon: Mapped[str] = mapped_column(String(24), nullable=False)  # immediate|short|long
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_factors: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(40), default="rules", nullable=False)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    station = relationship("Station")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                                index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), default="New conversation", nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan",
                            order_by="Message.id")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    grounding: Mapped[dict | None] = mapped_column(JSON)  # what data the answer used

    conversation = relationship("Conversation", back_populates="messages")
