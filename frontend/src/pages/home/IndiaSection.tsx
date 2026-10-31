import { useMemo, useState } from 'react'

import { ProvenanceBadge } from '@/components/Provenance'
import { ChartSkeleton, ErrorState } from '@/components/State'
import { IndiaMap, ZoneLegend } from '@/maps/IndiaMap'
import { AQI_CATEGORIES } from '@/lib/aqi'
import { num, relativeTime } from '@/lib/format'
import type { IndiaCity } from '@/lib/insights'
import { useSelection } from '@/lib/selection'

import { useIndia } from './LiveHero'
import { AqiBadge, Section, Segmented } from './shared'

export function IndiaSection() {
  const india = useIndia()
  const { citySlug, setCity } = useSelection()
  const pick = (slug: string) => {
    setCity(slug)
    document.getElementById('live')?.scrollIntoView({ behavior: 'smooth' })
  }
  const d = india.data

  return (
    <Section id="india" eyebrow="National Comparison" title="India Air Quality Index Rankings"
             lede="Comparative real-time and model-estimated air quality across Indian cities.
                   Circles are coloured by current AQI category — select any city to view its detailed analytics." tint
             action={d && <ProvenanceBadge provenance={d.provenance} />}>
      {india.isLoading ? <ChartSkeleton height={480} />
        : india.isError ? <ErrorState error={india.error} onRetry={() => india.refetch()} />
        : d && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[
              ['National average', num(d.national_average, 0), 'AQI (US)'],
              ['Cities tracked', String(d.reporting_cities), `of ${d.total_cities}`],
              [d.provenance?.mode === 'demo' ? 'Demo Mode' : 'Station Measured',
               String(d.measured_cities),
               d.provenance?.mode === 'demo' ? 'Synthetic reference stations' : `${d.station_count} stations reporting now`],
              ['Model Estimated', String((d.calibrated_cities ?? 0) + d.modelled_cities),
               d.provenance?.mode === 'demo' ? 'Synthetic model predictions' : 'CAMS model, calibrated to stations'],
            ].map(([label, value, sub]) => (
              <div key={label} className="card p-4">
                <p className="label-eyebrow">{label}</p>
                <p className="mt-1 text-3xl font-black tnum text-gradient">{value}</p>
                <p className="text-2xs font-semibold text-faint">{sub}</p>
              </div>
            ))}
          </div>

          <div className="card card-pad mt-4">
            <p className="text-xs font-bold text-ink">How many cities are in each band</p>
            <div className="mt-2 flex h-4 overflow-hidden rounded-full">
              {AQI_CATEGORIES.map((c) => {
                const n = d.by_category[c.key] ?? 0
                return n ? <span key={c.key} title={`${c.label}: ${n}`}
                                 style={{ flex: n, background: c.color }} /> : null
              })}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-2xs">
              {AQI_CATEGORIES.map((c) => (
                <span key={c.key} className="flex items-center gap-1.5 text-muted">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                  {c.label} <strong className="tnum text-ink">{d.by_category[c.key] ?? 0}</strong>
                </span>
              ))}
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <IndiaMap cities={d.cities} selectedSlug={citySlug} onSelect={pick}
                        height={560} />
              <div className="mt-3 card card-pad"><ZoneLegend /></div>
            </div>
            <div className="grid content-start gap-4">
              <RankList title="Most polluted right now" rows={d.worst} onPick={pick} numbered />
              <RankList title="Cleanest air right now" rows={d.cleanest} onPick={pick} />
            </div>
          </div>

          <StatesTable states={d.states} />
          <CityTable cities={d.cities} onPick={pick} current={citySlug} isDemo={d.provenance?.mode === 'demo'} />
        </>
      )}
    </Section>
  )
}

function RankList({ title, rows, onPick, numbered = false }: {
  title: string; rows: IndiaCity[]; onPick: (s: string) => void; numbered?: boolean }) {
  return (
    <div className="card overflow-hidden">
      <h3 className="border-b border-line px-4 py-2.5 text-sm font-bold text-ink">{title}</h3>
      <ul className="divide-y divide-line">
        {rows.slice(0, 8).map((c, i) => (
          <li key={c.slug}>
            <button type="button" onClick={() => onPick(c.slug)}
                    className="flex w-full items-center gap-3 px-4 py-2 text-left
                               transition-colors hover:bg-raised">
              {numbered && <span className="w-4 text-2xs tnum text-faint">{i + 1}</span>}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold text-ink">{c.name}</span>
                <span className="block truncate text-[10px] text-faint">{c.state}</span>
              </span>
              <AqiBadge aqi={c.aqi} color={c.category?.color} size="sm" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function StatesTable({ states }: { states: Array<{ state: string; aqi: number
  cities: number; category: { color: string; label: string } | null }> }) {
  const max = Math.max(1, ...states.map((s) => s.aqi))
  return (
    <div className="card card-pad mt-4">
      <h3 className="text-sm font-bold text-ink">States and union territories</h3>
      <p className="text-2xs text-faint">Average AQI of the tracked cities in each.</p>
      <ul className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {states.map((s) => (
          <li key={s.state} className="flex items-center gap-3">
            <span className="w-36 shrink-0 truncate text-xs font-semibold text-ink"
                  title={s.state}>{s.state}</span>
            <span className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-line/70">
              <span className="absolute inset-y-0 left-0 rounded-full"
                    style={{ width: `${(s.aqi / max) * 100}%`, background: s.category?.color }} />
            </span>
            <span className="w-8 text-right text-xs font-bold tnum"
                  style={{ color: s.category?.color }}>{s.aqi}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function CityTable({ cities, onPick, current, isDemo = false }:
  { cities: IndiaCity[]; onPick: (s: string) => void; current?: string; isDemo?: boolean }) {
  const [q, setQ] = useState('')
  const [order, setOrder] = useState<'worst' | 'best' | 'name'>('worst')
  const [showAll, setShowAll] = useState(false)
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const list = cities.filter((c) => c.aqi != null && (!needle
      || c.name.toLowerCase().includes(needle) || (c.state ?? '').toLowerCase().includes(needle)))
    list.sort((a, b) => order === 'name' ? a.name.localeCompare(b.name)
      : order === 'worst' ? (b.aqi ?? 0) - (a.aqi ?? 0) : (a.aqi ?? 0) - (b.aqi ?? 0))
    return list
  }, [cities, q, order])
  const visible = showAll || q ? rows : rows.slice(0, 25)

  return (
    <div className="card mt-4 overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center
                      sm:justify-between">
        <div>
          <h3 className="text-sm font-bold text-ink">All {rows.length} cities</h3>
          <p className="text-2xs text-faint">Search by city or state.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
                 aria-label="Search cities" className="input w-44 py-1.5 text-xs" />
          <Segmented label="Sort" value={order} onChange={setOrder}
                     options={[{ value: 'worst', label: 'Most polluted' },
                               { value: 'best', label: 'Cleanest' },
                               { value: 'name', label: 'A–Z' }]} />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-xs">
          <thead className="bg-raised/60 text-2xs uppercase tracking-wide text-faint">
            <tr>
              <th className="px-4 py-2 font-semibold">#</th>
              <th className="px-2 py-2 font-semibold">City</th>
              <th className="px-2 py-2 font-semibold">State</th>
              <th className="px-2 py-2 font-semibold">Status</th>
              <th className="px-2 py-2 font-semibold">Source</th>
              <th className="px-4 py-2 text-right font-semibold">AQI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {visible.map((c) => (
              <tr key={c.slug} onClick={() => onPick(c.slug)}
                  className={`cursor-pointer transition-colors hover:bg-raised ${
                    c.slug === current ? 'bg-brand-soft/60' : ''}`}>
                <td className="px-4 py-2 tnum text-faint">{c.rank ?? '—'}</td>
                <td className="px-2 py-2 font-semibold text-ink">{c.name}</td>
                <td className="px-2 py-2 text-muted">{c.state}</td>
                <td className="px-2 py-2 font-semibold" style={{ color: c.category?.color }}>
                  {c.category?.label}</td>
                <td className="px-2 py-2 text-faint">
                  {isDemo
                    ? 'Demo Est.'
                    : c.source === 'measured'
                    ? `${c.station_count} station${c.station_count === 1 ? '' : 's'}`
                    : c.source === 'calibrated' ? 'Calibrated Est.' : 'Model'}
                  {c.observed_at && <> · {relativeTime(c.observed_at)}</>}
                </td>
                <td className="px-4 py-2 text-right">
                  <AqiBadge aqi={c.aqi} color={c.category?.color} size="sm" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!q && rows.length > 25 && (
        <div className="border-t border-line p-3 text-center">
          <button type="button" className="btn-ghost py-1.5 text-xs"
                  onClick={() => setShowAll((v) => !v)}>
            {showAll ? 'Show top 25' : `Show all ${rows.length} cities`}
          </button>
        </div>
      )}
    </div>
  )
}
