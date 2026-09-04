import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

import { AqiPill } from '@/components/AqiGauge'
import { aqiColor, POLLUTANT_LABEL, ZONE_LABEL } from '@/lib/aqi'
import { compactNumber, num, relativeTime } from '@/lib/format'
import { useTheme } from '@/lib/theme'
import type { City, MapPoint } from '@/lib/types'

const LIGHT_TILES = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
const DARK_TILES = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION = '&copy; OpenStreetMap contributors &copy; CARTO'

function Recenter({ city }: { city: City }) {
  const map = useMap()
  useEffect(() => {
    map.setView([city.latitude, city.longitude], city.default_zoom, { animate: true })
  }, [city, map])
  return null
}

/** Marker radius encodes exposed population; colour encodes the AQI band.
 *  Two channels, two different quantities — never the same one twice. */
function radiusFor(population: number | null) {
  if (!population) return 10
  return Math.max(9, Math.min(24, 8 + Math.sqrt(population) / 90))
}

export function AirQualityMap({ city, points, selectedId, onSelect, height = 520 }: {
  city: City
  points: MapPoint[]
  selectedId?: number
  onSelect?: (stationId: number) => void
  height?: number
}) {
  const { resolved } = useTheme()
  const tiles = resolved === 'dark' ? DARK_TILES : LIGHT_TILES

  const ordered = useMemo(
    () => [...points].sort((a, b) => (a.aqi ?? 0) - (b.aqi ?? 0)), [points])

  return (
    <div className="overflow-hidden rounded-2xl border border-line"
         style={{ height }}>
      <MapContainer center={[city.latitude, city.longitude]}
                    zoom={city.default_zoom} scrollWheelZoom
                    style={{ height: '100%', width: '100%' }}>
        <TileLayer key={resolved} url={tiles} attribution={ATTRIBUTION}
                   maxZoom={19} />
        <Recenter city={city} />

        {ordered.map((point) => {
          const color = aqiColor(point.aqi)
          const selected = selectedId === point.station.id
          return (
            <CircleMarker
              key={point.station.id}
              center={[point.station.latitude, point.station.longitude]}
              radius={radiusFor(point.station.population_exposed)}
              pathOptions={{
                color: selected ? 'rgb(var(--c-ink))' : 'rgb(var(--c-surface))',
                weight: selected ? 3 : 2,       // 2px surface ring on overlap
                fillColor: color,
                fillOpacity: point.aqi === null ? 0.25 : 0.86,
              }}
              eventHandlers={{ click: () => onSelect?.(point.station.id) }}
            >
              <Tooltip direction="top" offset={[0, -6]} opacity={1}>
                <span className="text-xs font-medium">
                  {point.station.name} · AQI {point.aqi === null ? '—'
                    : Math.round(point.aqi)}
                </span>
              </Tooltip>
              <Popup>
                <div className="min-w-[240px] p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink">
                        {point.station.name}
                      </p>
                      <p className="text-2xs text-faint">
                        {ZONE_LABEL[point.station.zone_type] ?? point.station.zone_type}
                        {point.is_hotspot && ' · hotspot'}
                      </p>
                    </div>
                    <AqiPill aqi={point.aqi} />
                  </div>
                  <dl className="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-1 text-2xs">
                    <dt className="text-faint">PM2.5</dt>
                    <dd className="text-right tnum text-muted">
                      {num(point.pm25, 1)} µg/m³</dd>
                    <dt className="text-faint">PM10</dt>
                    <dd className="text-right tnum text-muted">
                      {num(point.pm10, 1)} µg/m³</dd>
                    <dt className="text-faint">Driver</dt>
                    <dd className="text-right text-muted">
                      {point.dominant_pollutant
                        ? POLLUTANT_LABEL[point.dominant_pollutant]
                          ?? point.dominant_pollutant
                        : '—'}</dd>
                    <dt className="text-faint">Exposed</dt>
                    <dd className="text-right tnum text-muted">
                      {compactNumber(point.station.population_exposed)}</dd>
                    <dt className="text-faint">Updated</dt>
                    <dd className="text-right text-muted">
                      {relativeTime(point.observed_at)}</dd>
                  </dl>
                  {onSelect && (
                    <button type="button"
                            onClick={() => onSelect(point.station.id)}
                            className="btn-ghost mt-3 w-full px-3 py-1.5 text-xs">
                      Focus this station
                    </button>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}

export function MapLegend({ categories }: {
  categories: Array<{ key: string; label: string; color: string }>
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {categories.map((c) => (
        <span key={c.key} className="inline-flex items-center gap-1.5 text-2xs
                                     text-muted">
          <span className="h-2.5 w-2.5 rounded-full" aria-hidden="true"
                style={{ backgroundColor: c.color }} />
          {c.label}
        </span>
      ))}
      <span className="ml-auto text-2xs text-faint">
        Marker size ∝ exposed population
      </span>
    </div>
  )
}
