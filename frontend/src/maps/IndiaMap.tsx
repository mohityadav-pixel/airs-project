import { useMemo } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

import { aqiColor, categoryFor } from '@/lib/aqi'
import { num, relativeTime } from '@/lib/format'
import { useTheme } from '@/lib/theme'

const LIGHT_TILES = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png'
const DARK_TILES = 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png'
const ATTRIBUTION = '&copy; OpenStreetMap contributors &copy; CARTO'

export interface IndiaCityPoint {
  slug: string
  name: string
  latitude: number
  longitude: number
  aqi: number | null
  observed_at?: string | null
  dominant_pollutant?: string | null
}

/**
 * National comparison map. Every city is a disc coloured by its AQI band, so
 * the reader sees the country's real geography of air quality — the
 * Indo-Gangetic plain against the coasts — in one glance.
 *
 * Zoom is capped and dragging is enabled but scroll-zoom is off: on a page you
 * scroll through, a map that swallows the wheel is a trap.
 */
export function IndiaMap({ cities, selectedSlug, onSelect, height = 520 }: {
  cities: IndiaCityPoint[]
  selectedSlug?: string
  onSelect?: (slug: string) => void
  height?: number
}) {
  const { resolved } = useTheme()
  const tiles = resolved === 'dark' ? DARK_TILES : LIGHT_TILES

  // Draw the cleanest first so the worst cities end up on top where they
  // overlap — the reader should never lose a hotspot behind a clean city.
  const ordered = useMemo(
    () => [...cities].filter((c) => c.aqi !== null)
      .sort((a, b) => (a.aqi ?? 0) - (b.aqi ?? 0)), [cities])

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-raised"
         style={{ height }}>
      <MapContainer center={[22.6, 79.5]} zoom={5} minZoom={4} maxZoom={9}
                    scrollWheelZoom={false}
                    style={{ height: '100%', width: '100%' }}>
        <TileLayer key={resolved} url={tiles} attribution={ATTRIBUTION} />
        {ordered.map((city) => {
          const selected = selectedSlug === city.slug
          const radius = selected ? 13 : 9
          return (
            <CircleMarker
              key={city.slug}
              center={[city.latitude, city.longitude]}
              radius={radius}
              pathOptions={{
                color: selected ? 'rgb(var(--c-ink))' : 'rgb(var(--c-surface))',
                weight: selected ? 3 : 1.75,
                fillColor: aqiColor(city.aqi),
                fillOpacity: 0.92,
              }}
              eventHandlers={{ click: () => onSelect?.(city.slug) }}
            >
              <Tooltip direction="top" offset={[0, -4]} opacity={1}>
                <span className="text-xs">
                  <strong>{city.name}</strong> · AQI {num(city.aqi, 0)}
                  <span className="ml-1 text-faint">
                    {categoryFor(city.aqi)?.label}
                  </span>
                  {city.observed_at && (
                    <span className="ml-1 text-faint">
                      · {relativeTime(city.observed_at)}
                    </span>
                  )}
                </span>
              </Tooltip>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}

/** Plain-language zone names beside the official band labels. */
export const ZONE_BANDS = [
  { key: 'good', label: 'Good', plain: 'Safe for everyone', color: '#00A86B',
    range: '0–50' },
  { key: 'moderate', label: 'Moderate', plain: 'Bearable', color: '#F4C542',
    range: '51–100' },
  { key: 'usg', label: 'Unhealthy for sensitive groups', plain: 'Minor concern',
    color: '#F08A24', range: '101–150' },
  { key: 'unhealthy', label: 'Unhealthy', plain: 'Major concern',
    color: '#E14B4B', range: '151–200' },
  { key: 'very_unhealthy', label: 'Very unhealthy', plain: 'Severe',
    color: '#8B5CF6', range: '201–300' },
  { key: 'hazardous', label: 'Hazardous', plain: 'Emergency', color: '#7E1F2B',
    range: '301+' },
]

export function ZoneLegend() {
  return (
    <ul className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3 lg:grid-cols-6">
      {ZONE_BANDS.map((band) => (
        <li key={band.key} className="flex items-start gap-2">
          <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
                aria-hidden="true" style={{ backgroundColor: band.color }} />
          <span className="min-w-0">
            <span className="block text-xs font-semibold text-ink">
              {band.plain}
            </span>
            <span className="block text-2xs tnum text-faint">
              AQI {band.range}
            </span>
          </span>
        </li>
      ))}
    </ul>
  )
}
