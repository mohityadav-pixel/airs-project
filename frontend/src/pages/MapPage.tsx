import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { ProvenanceBadge } from '@/components/Provenance'
import { CitySelector } from '@/components/Selectors'
import { ChartSkeleton, ErrorState } from '@/components/State'
import { AirQualityMap, MapLegend } from '@/maps/AirQualityMap'
import { api } from '@/lib/api'
import { ZONE_LABEL } from '@/lib/aqi'
import { compactNumber, num, relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'

type SortKey = 'aqi' | 'name' | 'population'

export default function MapPage() {
  const { citySlug, stationId, setStation } = useSelection()
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('aqi')
  const [hotspotsOnly, setHotspotsOnly] = useState(false)

  const mapData = useQuery({ queryKey: ['map', citySlug],
    queryFn: () => api.map(citySlug), enabled: Boolean(citySlug) })

  const rows = useMemo(() => {
    const points = mapData.data?.points ?? []
    const filtered = points.filter((p) => {
      if (hotspotsOnly && !p.is_hotspot) return false
      if (!query.trim()) return true
      const needle = query.trim().toLowerCase()
      return p.station.name.toLowerCase().includes(needle)
        || p.station.code.toLowerCase().includes(needle)
        || (ZONE_LABEL[p.station.zone_type] ?? '').toLowerCase().includes(needle)
    })
    return [...filtered].sort((a, b) => {
      if (sort === 'name') return a.station.name.localeCompare(b.station.name)
      if (sort === 'population')
        return (b.station.population_exposed ?? 0) - (a.station.population_exposed ?? 0)
      return (b.aqi ?? -1) - (a.aqi ?? -1)
    })
  }, [mapData.data, query, sort, hotspotsOnly])

  if (mapData.isLoading) return <ChartSkeleton height={520} />
  if (mapData.isError) {
    return <ErrorState error={mapData.error} onRetry={() => mapData.refetch()} />
  }
  if (!mapData.data) return null

  return (
    <>
      <PageHeader title="Live air quality map"
                  description="Every monitoring station in the city, coloured by AQI band and sized by the population in its catchment."
                  actions={<CitySelector />} />

      {/* Filters live in one row above the map, never inside it. */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
               placeholder="Search a station or area"
               aria-label="Search stations"
               className="input w-full max-w-xs py-2 text-sm" />
        <label className="inline-flex items-center gap-2">
          <span className="sr-only">Sort by</span>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}
                  className="input w-auto py-2 pr-8 text-sm">
            <option value="aqi">Worst first</option>
            <option value="name">Name</option>
            <option value="population">Most exposed</option>
          </select>
        </label>
        <label className="inline-flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={hotspotsOnly}
                 onChange={(e) => setHotspotsOnly(e.target.checked)}
                 className="h-4 w-4 rounded border-line accent-[rgb(var(--c-brand))]" />
          Hotspots only
        </label>
        <span className="ml-auto">
          <ProvenanceBadge provenance={mapData.data.provenance} />
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <AirQualityMap city={mapData.data.city} points={rows}
                         selectedId={stationId} onSelect={setStation} height={560} />
          <div className="mt-3">
            <MapLegend categories={mapData.data.legend} />
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold text-ink">
              {rows.length} station{rows.length === 1 ? '' : 's'}
            </h2>
            <p className="text-2xs text-faint">Select one to focus the map</p>
          </div>
          <ul className="max-h-[560px] divide-y divide-line overflow-y-auto">
            {rows.map((point) => (
              <li key={point.station.id}>
                <button type="button"
                        onClick={() => setStation(point.station.id)}
                        aria-current={stationId === point.station.id ? 'true' : undefined}
                        className={`flex w-full items-center gap-3 px-4 py-3 text-left
                                    transition-colors hover:bg-raised ${
                          stationId === point.station.id ? 'bg-brand/5' : ''}`}>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">
                      {point.station.name}
                      {point.is_hotspot && (
                        <span className="ml-1.5 rounded bg-unhealthy/15 px-1 py-px
                                         text-[9px] font-semibold uppercase
                                         tracking-wide text-unhealthy">hotspot</span>
                      )}
                    </p>
                    <p className="truncate text-2xs text-faint">
                      {ZONE_LABEL[point.station.zone_type] ?? point.station.zone_type}
                      {' · '}{compactNumber(point.station.population_exposed)} exposed
                      {' · '}{relativeTime(point.observed_at)}
                    </p>
                    <p className="mt-0.5 text-2xs tnum text-muted">
                      PM2.5 {num(point.pm25, 1)} · PM10 {num(point.pm10, 1)} µg/m³
                    </p>
                  </div>
                  <AqiPill aqi={point.aqi} />
                </button>
              </li>
            ))}
            {rows.length === 0 && (
              <li className="px-4 py-8 text-center text-xs text-muted">
                No stations match that filter.
              </li>
            )}
          </ul>
        </div>
      </div>
    </>
  )
}
