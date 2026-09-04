from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import DataProvenance


class CityOut(BaseModel):
    id: int
    slug: str
    name: str
    country: str
    latitude: float
    longitude: float
    population: int | None = None
    default_zoom: int
    aqi_scale: str
    station_count: int = 0


class StationOut(BaseModel):
    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    zone_type: str
    population_exposed: int | None = None
    near_major_road: bool
    near_industrial: bool
    near_construction: bool


class CategoryOut(BaseModel):
    key: str
    label: str
    color: str
    advice: str | None = None


class PollutantOut(BaseModel):
    key: str
    label: str
    concentration: float | None
    unit: str
    sub_index: float | None
    share_of_aqi: float | None = Field(
        default=None, description="This pollutant's sub-index as a share of the "
                                   "overall AQI (100% means it is the driver).")
    category: CategoryOut | None = None


class TrendOut(BaseModel):
    direction: str
    change: float | None = None
    change_pct: float | None = None


class WeatherOut(BaseModel):
    observed_at: datetime | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    wind_speed_mps: float | None = None
    wind_deg: float | None = None
    rain_1h_mm: float | None = None
    clouds_pct: float | None = None
    visibility_m: float | None = None
    condition: str | None = None
    ventilation_index: float | None = None


class TrafficOut(BaseModel):
    observed_at: datetime | None = None
    congestion_index: float | None = None
    speed_ratio: float | None = None
    vehicle_volume_est: float | None = None


class CurrentAirQuality(BaseModel):
    station: StationOut
    city: CityOut
    observed_at: datetime | None
    aqi: float | None
    category: CategoryOut | None
    dominant_pollutant: str | None
    pollutants: list[PollutantOut]
    trend_1h: TrendOut
    trend_24h: TrendOut
    weather: WeatherOut | None
    traffic: TrafficOut | None
    quality_flags: list[str] = []
    provenance: DataProvenance


class CitySummary(BaseModel):
    city: CityOut
    average_aqi: float | None
    worst_station: StationOut | None
    worst_aqi: float | None
    best_station: StationOut | None
    best_aqi: float | None
    category: CategoryOut | None
    dominant_pollutant: str | None
    station_count: int
    reporting_stations: int
    hotspot_station_ids: list[int]
    updated_at: datetime | None
    provenance: DataProvenance


class MapPoint(BaseModel):
    station: StationOut
    aqi: float | None
    category: CategoryOut | None
    dominant_pollutant: str | None
    pm25: float | None
    pm10: float | None
    observed_at: datetime | None
    is_hotspot: bool
    forecast_6h: float | None = None
    top_source: str | None = None


class MapResponse(BaseModel):
    city: CityOut
    points: list[MapPoint]
    legend: list[CategoryOut]
    provenance: DataProvenance


class SeriesPoint(BaseModel):
    at: datetime
    aqi: float | None = None
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    so2: float | None = None
    co: float | None = None
    o3: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_mps: float | None = None
    congestion_index: float | None = None


class HistoryResponse(BaseModel):
    station: StationOut
    points: list[SeriesPoint]
    stats: dict
    provenance: DataProvenance


class ForecastPoint(BaseModel):
    target_at: datetime
    horizon_hours: int
    aqi: float | None
    aqi_lower: float | None
    aqi_upper: float | None
    pm25: float | None
    pm10: float | None
    confidence: float
    risk_category: str | None
    tier: str


class ExplanationOut(BaseModel):
    headline: str
    simple: str
    technical: str
    factors: list[str]
    tier: str


class PredictionResponse(BaseModel):
    station: StationOut
    issued_at: datetime | None
    current_aqi: float | None
    horizons: list[ForecastPoint]
    curve: list[ForecastPoint]
    peak: ForecastPoint | None
    trough: ForecastPoint | None
    model: dict
    explanation: ExplanationOut | None
    provenance: DataProvenance


class SourceContribution(BaseModel):
    key: str
    label: str
    share_pct: float


class SourceResponse(BaseModel):
    station: StationOut
    contributions: list[SourceContribution]
    evidence: list[dict]
    confidence: float
    method: str
    provenance: DataProvenance
