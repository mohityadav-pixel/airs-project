/** Typed client for the /insights endpoints that power the dashboard. */
import { request } from './api'
import type { Provenance } from './types'

export interface Cat { key: string; label: string; color: string; advice?: string }

export interface CityMeta {
  slug: string; name: string; state: string | null
  latitude: number; longitude: number
}

export interface LiveStation {
  uid: number; name: string; full_name: string
  latitude: number; longitude: number
  aqi: number | null; category: Cat | null
  distance_km: number; observed_at: string | null
  network?: string; fresh?: boolean
}

export interface LivePollutant {
  key: string; label: string; concentration: number | null; unit: string
  sub_index: number | null; category: Cat | null; stations: number
}

export interface DailyWeather {
  date: string; code: number; condition: string | null
  t_max: number; t_min: number; rain_chance: number | null
  uv_max: number | null; wind_max: number | null
}

export interface LiveWeather {
  temperature_c: number | null; feels_like_c: number | null
  humidity_pct: number | null; pressure_hpa: number | null
  wind_speed_mps: number | null; wind_deg: number | null
  rain_mm: number | null; cloud_pct: number | null; uv_index: number | null
  visibility_m: number | null; is_day: boolean; code: number | null
  condition: string | null; daily: DailyWeather[]
}

export interface LiveCity {
  city: CityMeta
  aqi: number | null; category: Cat | null
  source: 'measured' | 'calibrated' | 'modelled'; source_label: string
  calibration_anchors?: number
  station_count: number; stations: LiveStation[]
  dominant_pollutant: string | null; pollutants: LivePollutant[]
  weather: LiveWeather | null
  yesterday: { aqi: number | null; change_pct: number | null }
  range_24h: { min: number | null; max: number | null }
  past_24h: Array<{ at: string; hours_ago: number; aqi: number | null
                    kind: 'observed' | 'estimated' }>
  calibration_factor: number
  observed_at: string; generated_at: string
  provenance: Provenance
}

export interface ForecastHour {
  at: string; hours_ahead: number; aqi: number | null; raw_model_aqi: number | null
  pm25: number | null; pm10: number | null; category: Cat | null
}

export interface Forecast {
  city: CityMeta; current_aqi: number | null
  hours: ForecastHour[]
  days: Array<{ date: string; min: number; max: number; avg: number
                category: Cat | null; weather: DailyWeather | null }>
  peak: ForecastHour | null; best_window: ForecastHour | null
  calibration_factor: number; provenance: Provenance
}

export interface History {
  city: CityMeta; metric: string; metric_label: string; unit: string
  month: number; years: number[]
  series: Array<{ year: number
                  days: Array<{ day: number; value: number | null
                                measured?: number | null }> }>
  monthly: Array<{ year: number; months: Array<number | null> }>
  calendar: Array<{ date: string; aqi: number | null; color: string | null }>
  summary: {
    this_year: HistoryStats | null; last_year: HistoryStats | null
    change_vs_last_year_pct: number | null
  }
  calibration: { applied: boolean; factor: number; days: number }
  provenance: Provenance
}

export interface HistoryStats {
  avg: number; best_day: number; best: number
  worst_day: number; worst: number; days: number
}

export interface IndiaCity extends CityMeta {
  aqi: number | null; category: Cat | null
  source: 'measured' | 'calibrated' | 'modelled'
  station_count: number; observed_at: string | null; rank?: number
}

export interface IndiaOverview {
  cities: IndiaCity[]; worst: IndiaCity[]; cleanest: IndiaCity[]
  national_average: number | null
  reporting_cities: number; total_cities: number
  measured_cities: number; calibrated_cities?: number
  modelled_cities: number; station_count: number
  by_category: Record<string, number>
  states: Array<{ state: string; aqi: number; cities: number; category: Cat | null }>
  generated_at: string; provenance: Provenance
}

export const insights = {
  cities: () => request<CityMeta[]>('/insights/cities'),
  live: (city: string) =>
    request<LiveCity>(`/insights/live?city=${encodeURIComponent(city)}`),
  forecast: (city: string) =>
    request<Forecast>(`/insights/forecast?city=${encodeURIComponent(city)}`),
  history: (city: string, month: number, metric: string) =>
    request<History>(`/insights/history?city=${encodeURIComponent(city)}`
      + `&month=${month}&metric=${metric}`),
  india: () => request<IndiaOverview>('/insights/india'),
}
