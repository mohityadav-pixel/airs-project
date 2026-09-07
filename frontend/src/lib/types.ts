/** Types mirroring the FastAPI response models. */

export type DataKind =
  | 'observed' | 'predicted' | 'simulated' | 'estimated' | 'ai_generated'
export type SourceMode = 'live' | 'cached' | 'demo'

export interface Provenance {
  kind: DataKind
  mode: SourceMode
  source: string
  observed_at?: string | null
  generated_at?: string | null
  note?: string | null
  is_stale: boolean
}

export interface City {
  id: number
  slug: string
  name: string
  country: string
  latitude: number
  longitude: number
  population: number | null
  default_zoom: number
  aqi_scale: string
  station_count: number
}

export interface Station {
  id: number
  code: string
  name: string
  latitude: number
  longitude: number
  zone_type: string
  population_exposed: number | null
  near_major_road: boolean
  near_industrial: boolean
  near_construction: boolean
}

export interface Category {
  key: string
  label: string
  color: string
  advice?: string | null
}

export interface Pollutant {
  key: string
  label: string
  concentration: number | null
  unit: string
  sub_index: number | null
  share_of_aqi: number | null
  category: Category | null
}

export interface Trend {
  direction: 'improving' | 'worsening' | 'stable' | 'unknown'
  change: number | null
  change_pct: number | null
}

export interface Weather {
  observed_at?: string | null
  temperature_c: number | null
  humidity_pct: number | null
  pressure_hpa: number | null
  wind_speed_mps: number | null
  wind_deg: number | null
  rain_1h_mm: number | null
  clouds_pct: number | null
  visibility_m: number | null
  condition: string | null
  ventilation_index: number | null
}

export interface Traffic {
  observed_at?: string | null
  congestion_index: number | null
  speed_ratio: number | null
  vehicle_volume_est: number | null
}

export interface CurrentAirQuality {
  station: Station
  city: City
  observed_at: string | null
  aqi: number | null
  category: Category | null
  dominant_pollutant: string | null
  pollutants: Pollutant[]
  trend_1h: Trend
  trend_24h: Trend
  weather: Weather | null
  traffic: Traffic | null
  quality_flags: string[]
  provenance: Provenance
}

export interface CitySummary {
  city: City
  average_aqi: number | null
  worst_station: Station | null
  worst_aqi: number | null
  best_station: Station | null
  best_aqi: number | null
  category: Category | null
  dominant_pollutant: string | null
  station_count: number
  reporting_stations: number
  hotspot_station_ids: number[]
  updated_at: string | null
  provenance: Provenance
}

export interface MapPoint {
  station: Station
  aqi: number | null
  category: Category | null
  dominant_pollutant: string | null
  pm25: number | null
  pm10: number | null
  observed_at: string | null
  is_hotspot: boolean
  forecast_6h: number | null
  top_source: string | null
}

export interface MapResponse {
  city: City
  points: MapPoint[]
  legend: Category[]
  provenance: Provenance
}

export interface SeriesPoint {
  at: string
  aqi: number | null
  pm25: number | null
  pm10: number | null
  no2: number | null
  so2: number | null
  co: number | null
  o3: number | null
  temperature_c: number | null
  humidity_pct: number | null
  wind_speed_mps: number | null
  congestion_index: number | null
}

export interface HistoryResponse {
  station: Station
  points: SeriesPoint[]
  stats: {
    count: number
    average_aqi: number | null
    max_aqi: number | null
    min_aqi: number | null
    peak_at: string | null
    cleanest_at: string | null
    average_pm25: number | null
    average_pm10: number | null
  }
  provenance: Provenance
}

export interface ForecastPoint {
  target_at: string
  horizon_hours: number
  aqi: number | null
  aqi_lower: number | null
  aqi_upper: number | null
  pm25: number | null
  pm10: number | null
  confidence: number
  risk_category: string | null
  tier: string
}

export interface Explanation {
  headline: string
  simple: string
  technical: string
  factors: string[]
  tier: string
}

export interface PredictionResponse {
  station: Station
  issued_at: string | null
  current_aqi: number | null
  horizons: ForecastPoint[]
  curve: ForecastPoint[]
  peak: ForecastPoint | null
  trough: ForecastPoint | null
  model: Record<string, unknown>
  explanation: Explanation | null
  provenance: Provenance
}

export interface SourceContribution {
  key: string
  label: string
  share_pct: number
}

export interface SourceEvidence {
  signal: string
  value: number | string
  reading: string
}

export interface SourceResponse {
  station: Station
  contributions: SourceContribution[]
  evidence: SourceEvidence[]
  confidence: number
  method: string
  provenance: Provenance
}

export interface Intervention {
  key: string
  label: string
  category: string
  description: string
  unit: string
  max_magnitude: number
  lag_hours: number
  cost_band: string
  evidence_note: string | null
  effectiveness: Record<string, number>
}

export interface SimulationResponse {
  station: Station | null
  baseline: {
    aqi: number | null
    category: Category | null
    dominant_pollutant: string | null
    concentrations: Record<string, number | null>
    sub_indices: Record<string, number>
  }
  simulated: SimulationResponse['baseline']
  deltas: {
    aqi: number | null
    improvement_pct: number | null
    pm25: number | null
    pm10: number | null
    category_changed: boolean
    exposure: { population_exposed: number; note: string } | null
  }
  per_lever: Array<{
    key: string
    label: string
    magnitude_pct: number
    attributable_source_share_pct: number
    pollutant_reduction_pct: Record<string, number>
  }>
  assumptions: string[]
  warnings: string[]
  confidence: number
  engine_version: string
  caveat: string
  provenance: Provenance
}

export interface Recommendation {
  action: string
  reason: string
  expected_impact: string
  intervention_key: string | null
  time_horizon: string
  priority_score: number
  priority_factors: Record<string, {
    value: number | null
    weight: number
    raw: number | null
    explanation: string
  }>
  confidence: number
  station_id: number | null
  station_name: string | null
  modelled_improvement_pct: number | null
}

export interface RecommendationResponse {
  city_slug: string
  generated_at: string
  immediate: Recommendation[]
  short_term: Recommendation[]
  long_term: Recommendation[]
  methodology: Record<string, string>
  provenance: Provenance
}

export interface Alert {
  id: number
  kind: string
  severity: 'info' | 'watch' | 'warning' | 'emergency'
  title: string
  what_happened: string
  why_it_matters: string
  recommended_action: string
  expected_duration_hours: number | null
  raised_at: string
  expires_at: string | null
  station_id: number | null
  station_name: string | null
  context: Record<string, unknown> | null
}

export interface HealthAdvisory {
  available: boolean
  group?: string
  group_label?: string
  aqi?: number
  effective_aqi_for_group?: number
  category?: Category | null
  risk_level?: string
  outdoor_activity?: string
  exercise?: string
  mask?: string
  ventilation?: string
  exposure_reduction?: string[]
  notes?: string[]
  disclaimer: string
  message?: string
  station?: { id: number; name: string }
  observed_at?: string | null
}

export type Role = 'citizen' | 'analyst' | 'official' | 'admin'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  sensitivity_group: string
  home_city_id: number | null
}

export interface SystemStatus {
  service: string
  environment: string
  data_mode: 'live' | 'demo' | 'auto'
  capabilities: {
    data_mode: string
    air_quality_provider: boolean
    weather_provider: boolean
    traffic_provider: boolean
    ai_copilot: boolean
    ml_models_trained: boolean
  }
  data: {
    live_readings: number
    demo_readings: number
    total_readings: number
    note: string
  }
  model: {
    trained_at: string | null
    model_name: string | null
    model_version: string | null
    reports: Array<{
      target: string
      horizon_hours: number
      mae: number
      r2: number
      baseline_mae: number
      skill_vs_persistence: number
      n_train: number
      n_test: number
    }>
  }
  provider_failures?: Record<string, {
    error: string
    message: string
    seconds_ago: number
  }>
  server_time: string
}

export interface CommandCenterZone {
  station: Station
  aqi: number | null
  category: Category | null
  pm25: number | null
  pm10: number | null
  observed_at: string
  is_hotspot: boolean
  predicted_peak_aqi: number | null
  hours_to_peak: number | null
  expected_change: number | null
  top_source: string | null
  top_source_label: string | null
  source_confidence: number | null
  best_lever: string | null
  best_lever_improvement_pct: number | null
  priority_score: number
  priority_factors: Recommendation['priority_factors']
  priority_rationale: string
}

export interface CommandCenterResponse {
  city: City
  generated_at: string
  headline: {
    average_aqi: number | null
    worst_aqi: number | null
    stations_reporting: number
    stations_total: number
    hotspot_count: number
    deteriorating_count: number
    active_alerts: number
    population_in_hotspots: number
  }
  zones: CommandCenterZone[]
  deteriorating: CommandCenterZone[]
  alerts: Array<Pick<Alert, 'id' | 'severity' | 'title' | 'what_happened'
    | 'why_it_matters' | 'recommended_action' | 'station_name' | 'raised_at'>>
  methodology: Record<string, string>
}

export interface CopilotResponse {
  answer: string
  grounding: { facts: string[]; station: Record<string, unknown>; city: Record<string, unknown> }
  conversation_id: number | null
  generated_at: string
  suggested_questions: string[]
  provenance: Provenance
}
