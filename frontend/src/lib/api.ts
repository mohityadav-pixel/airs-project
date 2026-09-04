/**
 * Typed API client.
 *
 * One place that knows the wire format, so components never touch fetch and a
 * backend error always arrives as the same `ApiError` shape.
 */
import type {
  Alert, City, CommandCenterResponse, CopilotResponse, CurrentAirQuality,
  HealthAdvisory, HistoryResponse, Intervention, MapResponse, PredictionResponse,
  RecommendationResponse, SimulationResponse, SourceResponse, Station,
  CitySummary, SystemStatus, User,
} from './types'

const BASE = '/api/v1'
const TOKEN_KEY = 'airs.token'

export class ApiError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* private mode — session-only auth is acceptable */ }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers as Record<string, string> | undefined),
  }

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(
      'Could not reach the AIRS server. Check that the backend is running.',
      'network_error', 0)
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  const payload = text ? safeJson(text) : null

  if (!response.ok) {
    const err = (payload as { error?: { message?: string; code?: string } })?.error
    const detail = (payload as { detail?: unknown })?.detail
    throw new ApiError(
      err?.message ?? (typeof detail === 'string' ? detail : 'Request failed.'),
      err?.code ?? 'request_failed', response.status)
  }
  return payload as T
}

function safeJson(text: string): unknown {
  try { return JSON.parse(text) } catch { return null }
}

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  })
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const api = {
  status: () => request<SystemStatus>('/system/status'),

  cities: () => request<City[]>('/air-quality/cities'),
  stations: (city?: string) =>
    request<Station[]>(`/air-quality/stations${qs({ city })}`),
  current: (city?: string, stationId?: number) =>
    request<CurrentAirQuality>(`/air-quality/current${qs({ city, station_id: stationId })}`),
  summary: (city?: string) =>
    request<CitySummary>(`/air-quality/summary${qs({ city })}`),
  map: (city?: string) => request<MapResponse>(`/air-quality/map${qs({ city })}`),
  history: (p: { city?: string; stationId?: number; hours?: number;
                 start?: string; end?: string }) =>
    request<HistoryResponse>(`/air-quality/history${qs({
      city: p.city, station_id: p.stationId, hours: p.hours,
      start: p.start, end: p.end })}`),

  predictions: (city?: string, stationId?: number, curveHours = 24) =>
    request<PredictionResponse>(`/predictions${qs({
      city, station_id: stationId, curve_hours: curveHours })}`),

  sources: (city?: string, stationId?: number) =>
    request<SourceResponse>(`/pollution-sources${qs({ city, station_id: stationId })}`),

  pollutantAnalytics: (city?: string, stationId?: number, hours = 168) =>
    request<{ station: Station; window_hours: number; pollutants: Array<{
      key: string; label: string; unit: string; current: number | null
      average_24h: number | null; average_7d: number | null; min: number
      max: number; correlation_with_aqi: number | null
      times_dominant_pct: number; share_of_aqi_now: number | null }> }>(
      `/analytics/pollutants${qs({ city, station_id: stationId, hours })}`),

  correlations: (city?: string, stationId?: number, hours = 336) =>
    request<{ station: Station; window_hours: number; sample_size: number
      correlations: Array<{ driver: string; vs_aqi: number | null
        vs_pm25: number | null; interpretation: string }>; note: string }>(
      `/analytics/correlations${qs({ city, station_id: stationId, hours })}`),

  compare: (city?: string, stationId?: number, mode: 'day' | 'week' | 'month' = 'day') =>
    request<{ station: Station; mode: string; change_pct: number | null
      verdict: string
      current: Record<string, number | null>
      previous: Record<string, number | null> }>(
      `/analytics/compare${qs({ city, station_id: stationId, mode })}`),

  hourlyProfile: (city?: string, stationId?: number, days = 30) =>
    request<{ station: Station; days: number
      by_hour: Array<{ hour: number; average_aqi: number | null; samples: number }>
      by_weekday: Array<{ weekday: number; label: string
        average_aqi: number | null; samples: number }>; note: string }>(
      `/analytics/hourly-profile${qs({ city, station_id: stationId, days })}`),

  stationRanking: (city?: string, hours = 24) =>
    request<{ city: string; window_hours: number; stations: Array<{
      station: Station; average_aqi: number | null; max_aqi: number
      average_pm25: number | null; population_exposed: number | null
      zone_type: string }> }>(
      `/analytics/station-ranking${qs({ city, hours })}`),

  interventions: () => request<Intervention[]>('/simulation/interventions'),
  simulate: (body: { city_slug?: string; station_id?: number
                     levers: Array<{ key: string; magnitude: number }>
                     name?: string; save?: boolean }) =>
    request<SimulationResponse>('/simulation', {
      method: 'POST', body: JSON.stringify(body) }),

  recommendations: (city?: string) =>
    request<RecommendationResponse>(`/recommendations${qs({ city })}`),

  alerts: (city?: string) => request<Alert[]>(`/alerts${qs({ city })}`),

  healthAdvisory: (city?: string, stationId?: number, group?: string) =>
    request<HealthAdvisory>(`/health-advisory${qs({
      city, station_id: stationId, group })}`),
  healthGroups: () =>
    request<Array<{ key: string; label: string }>>('/health-advisory/groups'),

  copilotSuggestions: () =>
    request<{ available: boolean; questions: string[] }>('/copilot/suggestions'),
  copilot: (body: { question: string; city_slug?: string; station_id?: number
                    conversation_id?: number | null }) =>
    request<CopilotResponse>('/copilot', {
      method: 'POST', body: JSON.stringify(body) }),

  commandCenter: (city?: string) =>
    request<CommandCenterResponse>(`/command-center${qs({ city })}`),

  login: (email: string, password: string) =>
    request<{ access_token: string; expires_in_minutes: number }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (body: { email: string; full_name: string; password: string
                     home_city_slug?: string; sensitivity_group?: string }) =>
    request<{ access_token: string; expires_in_minutes: number }>('/auth/register', {
      method: 'POST', body: JSON.stringify(body) }),
  me: () => request<User>('/auth/me'),
  updateMe: (body: Partial<{ full_name: string; home_city_slug: string
                             sensitivity_group: string }>) =>
    request<User>('/auth/me', { method: 'PATCH', body: JSON.stringify(body) }),
}
