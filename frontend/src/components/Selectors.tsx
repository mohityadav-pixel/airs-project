import { useSelection } from '@/lib/selection'
import { ZONE_LABEL } from '@/lib/aqi'

export function CitySelector({ compact = false }: { compact?: boolean }) {
  const { cities, citySlug, setCity } = useSelection()
  return (
    <label className="inline-flex items-center gap-2">
      <span className="sr-only">City</span>
      <select value={citySlug ?? ''} onChange={(e) => setCity(e.target.value)}
              className={`input ${compact ? 'py-1.5 text-xs' : 'py-2 text-sm'}
                          w-auto min-w-[9rem] pr-8`}>
        {cities.map((c) => (
          <option key={c.slug} value={c.slug}>{c.name}</option>
        ))}
      </select>
    </label>
  )
}

export function StationSelector({ allowAll = true, compact = false }:
  { allowAll?: boolean; compact?: boolean }) {
  const { stations, stationId, setStation } = useSelection()
  return (
    <label className="inline-flex items-center gap-2">
      <span className="sr-only">Monitoring station</span>
      <select
        value={stationId ?? ''}
        onChange={(e) => setStation(e.target.value ? Number(e.target.value) : undefined)}
        className={`input ${compact ? 'py-1.5 text-xs' : 'py-2 text-sm'}
                    w-auto min-w-[11rem] pr-8`}
      >
        {allowAll && <option value="">Worst reporting station</option>}
        {stations.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} · {ZONE_LABEL[s.zone_type] ?? s.zone_type}
          </option>
        ))}
      </select>
    </label>
  )
}
