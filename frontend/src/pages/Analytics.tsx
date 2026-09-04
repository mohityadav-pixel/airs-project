import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { CitySelector, StationSelector } from '@/components/Selectors'
import { StatTile } from '@/components/StatTile'
import { CardSkeleton, ChartSkeleton, ErrorState } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { CorrelationBars } from '@/charts/CorrelationBars'
import { HourProfile } from '@/charts/HourProfile'
import { TrendChart } from '@/charts/TrendChart'
import { api } from '@/lib/api'
import { ZONE_LABEL } from '@/lib/aqi'
import { compactNumber, fmtDateTime, num } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import type { SeriesPoint } from '@/lib/types'

const RANGES = [
  { label: '24 h', hours: 24 },
  { label: '7 days', hours: 168 },
  { label: '30 days', hours: 720 },
  { label: '90 days', hours: 2160 },
]

const METRICS: Array<{ key: keyof SeriesPoint; label: string; unit: string }> = [
  { key: 'aqi', label: 'AQI', unit: '' },
  { key: 'pm25', label: 'PM2.5', unit: 'µg/m³' },
  { key: 'pm10', label: 'PM10', unit: 'µg/m³' },
  { key: 'no2', label: 'NO₂', unit: 'ppb' },
  { key: 'o3', label: 'O₃', unit: 'ppb' },
]

export default function Analytics() {
  const { citySlug, stationId, setStation } = useSelection()
  const [hours, setHours] = useState(168)
  const [metric, setMetric] = useState<keyof SeriesPoint>('aqi')
  const [compareMode, setCompareMode] = useState<'day' | 'week' | 'month'>('day')

  const history = useQuery({ queryKey: ['history', citySlug, stationId, hours],
    queryFn: () => api.history({ city: citySlug, stationId, hours }),
    enabled: Boolean(citySlug) })
  const pollutants = useQuery({ queryKey: ['pollutant-analytics', citySlug, stationId, hours],
    queryFn: () => api.pollutantAnalytics(citySlug, stationId, hours),
    enabled: Boolean(citySlug) })
  const correlations = useQuery({ queryKey: ['correlations', citySlug, stationId],
    queryFn: () => api.correlations(citySlug, stationId), enabled: Boolean(citySlug) })
  const profile = useQuery({ queryKey: ['profile', citySlug, stationId],
    queryFn: () => api.hourlyProfile(citySlug, stationId), enabled: Boolean(citySlug) })
  const comparison = useQuery({ queryKey: ['compare', citySlug, stationId, compareMode],
    queryFn: () => api.compare(citySlug, stationId, compareMode),
    enabled: Boolean(citySlug) })
  const ranking = useQuery({ queryKey: ['ranking', citySlug, hours],
    queryFn: () => api.stationRanking(citySlug, Math.min(hours, 720)),
    enabled: Boolean(citySlug) })

  const activeMetric = METRICS.find((m) => m.key === metric)!

  return (
    <>
      <PageHeader title="Historical analytics"
                  description="Trends, drivers and comparisons across the station network."
                  actions={<><CitySelector /><StationSelector /></>} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-xl border border-line bg-surface p-0.5">
          {RANGES.map((r) => (
            <button key={r.hours} type="button" onClick={() => setHours(r.hours)}
                    aria-pressed={hours === r.hours}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                      hours === r.hours ? 'bg-brand text-white'
                                        : 'text-muted hover:text-ink'}`}>
              {r.label}
            </button>
          ))}
        </div>
        <label className="inline-flex items-center gap-2">
          <span className="sr-only">Metric</span>
          <select value={String(metric)}
                  onChange={(e) => setMetric(e.target.value as keyof SeriesPoint)}
                  className="input w-auto py-1.5 pr-8 text-xs">
            {METRICS.map((m) => (
              <option key={String(m.key)} value={String(m.key)}>{m.label}</option>
            ))}
          </select>
        </label>
      </div>

      {history.isError && (
        <ErrorState error={history.error} onRetry={() => history.refetch()} />
      )}

      {history.data && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile label="Average AQI" value={num(history.data.stats.average_aqi, 0)}
                    footnote={`${history.data.stats.count} hourly readings`} />
          <StatTile label="Peak AQI" value={num(history.data.stats.max_aqi, 0)}
                    footnote={fmtDateTime(history.data.stats.peak_at)}
                    deltaTone="bad" />
          <StatTile label="Cleanest AQI" value={num(history.data.stats.min_aqi, 0)}
                    footnote={fmtDateTime(history.data.stats.cleanest_at)}
                    deltaTone="good" />
          <StatTile label="Average PM2.5"
                    value={num(history.data.stats.average_pm25, 1)} unit="µg/m³"
                    footnote={`PM10 ${num(history.data.stats.average_pm10, 1)} µg/m³`} />
        </div>
      )}

      <section className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {history.isLoading ? <ChartSkeleton /> : history.data ? (
            <ChartFrame title={`${activeMetric.label} over time`}
                        subtitle={history.data.station.name}
                        provenance={history.data.provenance}>
              <TrendChart points={history.data.points} dataKey={metric}
                          label={activeMetric.label} unit={activeMetric.unit}
                          height={280} />
            </ChartFrame>
          ) : null}
        </div>

        <div className="card card-pad">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-ink">Period comparison</h2>
            <select value={compareMode}
                    onChange={(e) =>
                      setCompareMode(e.target.value as 'day' | 'week' | 'month')}
                    className="input w-auto py-1 pr-7 text-xs">
              <option value="day">Today vs yesterday</option>
              <option value="week">This week vs last</option>
              <option value="month">This month vs last</option>
            </select>
          </div>
          {comparison.isLoading ? <div className="skeleton h-28 w-full" />
            : comparison.data ? (
              <>
                <p className="text-3xl font-semibold tnum text-ink">
                  {comparison.data.change_pct === null ? '—'
                    : `${comparison.data.change_pct > 0 ? '+' : ''}${
                        comparison.data.change_pct}%`}
                </p>
                <p className="mt-1 text-xs capitalize text-muted">
                  {comparison.data.verdict}
                </p>
                <dl className="mt-4 space-y-2 border-t border-line pt-3 text-xs">
                  {(['average_aqi', 'max_aqi', 'average_pm25'] as const).map((key) => (
                    <div key={key} className="flex items-center justify-between gap-3">
                      <dt className="capitalize text-faint">
                        {key.replace(/_/g, ' ')}</dt>
                      <dd className="tnum text-muted">
                        {num(comparison.data!.previous[key], 1)}
                        <span className="mx-1.5 text-faint">→</span>
                        <span className="font-medium text-ink">
                          {num(comparison.data!.current[key], 1)}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
              </>
            ) : null}
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-2">
        {correlations.isLoading ? <ChartSkeleton /> : correlations.data ? (
          <ChartFrame title="What moves AQI at this station"
                      subtitle={`Pearson r over ${correlations.data.window_hours} hours · ${correlations.data.sample_size} samples`}
                      footnote={correlations.data.note}>
            <CorrelationBars rows={correlations.data.correlations} />
          </ChartFrame>
        ) : null}

        {profile.isLoading ? <ChartSkeleton /> : profile.data ? (
          <ChartFrame title="Average AQI by hour of day"
                      subtitle={`${profile.data.days}-day profile · ${profile.data.note}`}
                      footnote="Bars are coloured by AQI band. The twin peaks are the
                                commuting cycle; the overnight rise is the shallow
                                nocturnal mixing layer, not new emissions.">
            <HourProfile byHour={profile.data.by_hour} />
          </ChartFrame>
        ) : null}
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-2">
        {pollutants.isLoading ? <CardSkeleton lines={6} /> : pollutants.data ? (
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Pollutant detail</h2>
            <p className="mt-1 text-xs text-muted">
              Over the selected window at {pollutants.data.station.name}.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-line text-2xs uppercase
                                 tracking-wide text-faint">
                    <th scope="col" className="py-2 pr-3 font-medium">Pollutant</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">Now</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">24 h</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">7 d</th>
                    <th scope="col" className="py-2 pr-3 text-right font-medium">r vs AQI</th>
                    <th scope="col" className="py-2 text-right font-medium">Dominant</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {pollutants.data.pollutants.map((p) => (
                    <tr key={p.key}>
                      <th scope="row" className="py-2 pr-3 font-medium text-ink">
                        {p.label}
                        <span className="ml-1 font-normal text-faint">{p.unit}</span>
                      </th>
                      <td className="py-2 pr-3 text-right tnum text-ink">
                        {num(p.current, 1)}</td>
                      <td className="py-2 pr-3 text-right tnum text-muted">
                        {num(p.average_24h, 1)}</td>
                      <td className="py-2 pr-3 text-right tnum text-muted">
                        {num(p.average_7d, 1)}</td>
                      <td className="py-2 pr-3 text-right tnum text-muted">
                        {p.correlation_with_aqi === null ? '—'
                          : p.correlation_with_aqi.toFixed(2)}</td>
                      <td className="py-2 text-right tnum text-muted">
                        {num(p.times_dominant_pct, 0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {ranking.isLoading ? <CardSkeleton lines={6} /> : ranking.data ? (
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Station ranking</h2>
            <p className="mt-1 text-xs text-muted">
              Worst average AQI over the last {ranking.data.window_hours} hours.
            </p>
            <ul className="mt-3 divide-y divide-line">
              {ranking.data.stations.map((row, i) => (
                <li key={row.station.id}>
                  <button type="button" onClick={() => setStation(row.station.id)}
                          className="flex w-full items-center gap-3 py-2.5 text-left
                                     hover:bg-raised">
                    <span className="w-5 shrink-0 text-2xs tnum text-faint">
                      {i + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-medium text-ink">
                        {row.station.name}</span>
                      <span className="block truncate text-2xs text-faint">
                        {ZONE_LABEL[row.zone_type] ?? row.zone_type} ·{' '}
                        {compactNumber(row.population_exposed)} exposed</span>
                    </span>
                    <AqiPill aqi={row.average_aqi} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </>
  )
}
