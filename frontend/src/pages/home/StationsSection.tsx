import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

import { num, relativeTime } from '@/lib/format'
import { useTheme } from '@/lib/theme'

import { useLive } from './LiveHero'
import { AqiBadge, Section } from './shared'

const LIGHT = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
const DARK = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'

function Fit({ points }: { points: Array<[number, number]> }) {
  const map = useMap()
  useEffect(() => {
    map.invalidateSize()
    const timer = setTimeout(() => {
      map.invalidateSize()
    }, 200)
    if (points.length === 1) map.setView(points[0], 11)
    else if (points.length > 1) map.fitBounds(points, { padding: [30, 30], maxZoom: 12 })
    return () => clearTimeout(timer)
  }, [map, points])
  return null
}

export function StationsSection() {
  const live = useLive()
  const { resolved } = useTheme()
  const [sort, setSort] = useState<'aqi' | 'distance'>('aqi')
  const data = live.data
  const stations = useMemo(() => [...(data?.stations ?? [])].sort((a, b) =>
    sort === 'aqi' ? (b.aqi ?? 0) - (a.aqi ?? 0) : a.distance_km - b.distance_km),
    [data, sort])
  const points = useMemo<Array<[number, number]>>(() =>
    data ? (data.stations.length ? data.stations.map((s) => [s.latitude, s.longitude])
      : [[data.city.latitude, data.city.longitude]]) : [],
    [data])
  if (!data) return null

  return (
    <Section id="stations" eyebrow="Monitoring Network"
      title={`${data.city.name} Monitoring Stations`}
      lede={data.source === 'measured'
        ? `${data.stations.length} station${data.stations.length === 1 ? '' : 's'} reported in the last three hours. The city AQI above is their average.`
        : data.stations.length
          ? 'None of these stations has reported in the last three hours, so their last readings are used only to correct the model — not shown as the current AQI.'
          : 'No physical monitoring stations are reporting in this city radius. AIRS displays regional Copernicus (CAMS) atmospheric model estimates.'}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="relative overflow-hidden rounded-2xl border border-line" style={{ height: 420 }}>
          <MapContainer center={points[0] ?? [22, 79]} zoom={11} scrollWheelZoom={false}
            style={{ height: '100%', width: '100%' }}>
            <TileLayer key={resolved} url={resolved === 'dark' ? DARK : LIGHT}
              attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"
              maxNativeZoom={16} maxZoom={19} />
            <Fit points={points} />
            {data.stations.map((s) => (
              <CircleMarker key={s.uid} center={[s.latitude, s.longitude]} radius={13}
                pathOptions={{
                  color: '#fff', weight: 2,
                  fillColor: s.category?.color ?? '#94a3b8',
                  fillOpacity: 0.95
                }}>
                <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={data.stations.length <= 6}>
                  <span className="text-xs font-bold">{s.aqi}</span>
                </Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
          {data.stations.length === 0 && (
            <div className="pointer-events-none absolute inset-x-4 bottom-4 z-[400] flex justify-center">
              <div className="rounded-xl border border-line bg-surface/90 px-4 py-2 text-center text-xs font-medium text-muted shadow-lg backdrop-blur">
                No active ground monitoring stations in {data.city.name}. Showing regional city coordinates.
              </div>
            </div>
          )}
        </div>

        <div className="card flex max-h-[420px] flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h3 className="text-sm font-bold text-ink">Locations</h3>
            <div className="flex gap-1 text-2xs">
              {(['aqi', 'distance'] as const).map((k) => (
                <button key={k} type="button" onClick={() => setSort(k)}
                  className={`rounded-full px-2.5 py-1 font-semibold ${sort === k ? 'bg-brand text-white' : 'text-muted hover:text-brand'}`}>
                  {k === 'aqi' ? 'Most polluted' : 'Nearest'}
                </button>
              ))}
            </div>
          </div>
          <ul className="divide-y divide-line overflow-y-auto">
            {stations.map((s) => (
              <li key={s.uid} className="flex items-center gap-3 px-4 py-2.5">
                <AqiBadge aqi={s.aqi} color={s.category?.color} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-ink"
                    title={s.full_name}>{s.name}</p>
                  <p className="text-2xs text-faint">
                    {s.category?.label} · {num(s.distance_km, 1)} km · {s.network}
                    {' · '}<span className={s.fresh === false ? 'font-semibold text-usg' : ''}>
                      {s.fresh === false ? 'last reading ' : ''}{relativeTime(s.observed_at)}</span>
                  </p>
                </div>
              </li>
            ))}
            {stations.length === 0 && (
              <li className="px-4 py-10 text-center text-xs text-muted">
                No station within reach. Showing the model estimate.
              </li>
            )}
          </ul>
        </div>
      </div>
    </Section>
  )
}
