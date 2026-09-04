import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { ProvenanceBadge } from '@/components/Provenance'
import { CitySelector, StationSelector } from '@/components/Selectors'
import { StatTile } from '@/components/StatTile'
import { ChartSkeleton, ErrorState } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { ForecastChart } from '@/charts/ForecastChart'
import { api } from '@/lib/api'
import { fmtDateTime, num, relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'

const HORIZON_OPTIONS = [12, 24, 48, 72]

export default function Predictions() {
  const { citySlug, stationId } = useSelection()
  const [curveHours, setCurveHours] = useState(24)

  const prediction = useQuery({
    queryKey: ['prediction', citySlug, stationId, curveHours],
    queryFn: () => api.predictions(citySlug, stationId, curveHours),
    enabled: Boolean(citySlug) })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status,
    staleTime: 300_000 })

  if (prediction.isLoading) return <ChartSkeleton height={320} />
  if (prediction.isError) {
    return <ErrorState error={prediction.error} onRetry={() => prediction.refetch()} />
  }
  const data = prediction.data
  if (!data) return null

  const tier = String((data.model as { tier?: string }).tier ?? 'unknown')
  const reports = status.data?.model.reports ?? []
  const aqiReports = reports.filter((r) => r.target === 'aqi')

  return (
    <>
      <PageHeader
        title="AQI forecast"
        description="Where air quality is heading at this station, with the model's own uncertainty and the reasoning behind it."
        actions={<><CitySelector /><StationSelector /></>}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="label-eyebrow">Horizon</span>
        <div className="inline-flex rounded-xl border border-line bg-surface p-0.5">
          {HORIZON_OPTIONS.map((h) => (
            <button key={h} type="button" onClick={() => setCurveHours(h)}
                    aria-pressed={curveHours === h}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium
                                transition-colors ${
                      curveHours === h ? 'bg-brand text-white'
                                       : 'text-muted hover:text-ink'}`}>
              {h} h
            </button>
          ))}
        </div>
        <span className="ml-auto"><ProvenanceBadge provenance={data.provenance} /></span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Now" value={num(data.current_aqi, 0)} unit="AQI"
                  footnote={`Measured ${relativeTime(data.issued_at)}`} />
        {data.horizons.map((h) => (
          <StatTile key={h.horizon_hours}
            label={`In ${h.horizon_hours} h`}
            value={num(h.aqi, 0)} unit="AQI"
            delta={data.current_aqi != null && h.aqi != null
              ? `${h.aqi > data.current_aqi ? '▲' : '▼'} ${
                  num(Math.abs(h.aqi - data.current_aqi), 0)}`
              : undefined}
            deltaTone={data.current_aqi != null && h.aqi != null
              ? (h.aqi > data.current_aqi ? 'bad' : 'good') : 'neutral'}
            footnote={`80% range ${num(h.aqi_lower, 0)}–${num(h.aqi_upper, 0)} · ${
              Math.round(h.confidence * 100)}% confidence`} />
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ChartFrame title={`Next ${curveHours} hours`}
                      subtitle={`Model ${String((data.model as { model_name?: string }).model_name)} · ${tier} tier · issued ${relativeTime(data.issued_at)}`}
                      provenance={data.provenance}
                      footnote="Anchor points come from the 6/24/72-hour models;
                                intermediate hours are interpolated and re-shaped
                                by the station's own diurnal profile.">
            <ForecastChart curve={data.curve} currentAqi={data.current_aqi}
                           height={320} />
          </ChartFrame>
        </div>

        <div className="grid content-start gap-4">
          {data.explanation && (
            <div className="card card-pad">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h2 className="text-sm font-semibold text-ink">
                  {data.explanation.headline}
                </h2>
              </div>
              <p className="text-sm leading-relaxed text-muted">
                {data.explanation.simple}
              </p>
              <h3 className="mt-3 text-2xs font-semibold uppercase tracking-wide
                             text-faint">Contributing factors</h3>
              <ul className="mt-1.5 space-y-1.5">
                {data.explanation.factors.map((f) => (
                  <li key={f} className="flex gap-2 text-xs text-muted">
                    <span aria-hidden="true" className="text-brand">—</span>{f}
                  </li>
                ))}
              </ul>
              <details className="mt-3">
                <summary className="cursor-pointer text-xs text-brand">
                  Technical explanation
                </summary>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {data.explanation.technical}
                </p>
              </details>
            </div>
          )}

          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Peaks and troughs</h2>
            <dl className="mt-3 space-y-3 text-xs">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <dt className="font-medium text-ink">Predicted peak</dt>
                  <dd className="text-2xs text-faint">
                    {data.peak ? fmtDateTime(data.peak.target_at) : '—'}</dd>
                </div>
                <AqiPill aqi={data.peak?.aqi ?? null} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <dt className="font-medium text-ink">Cleanest window</dt>
                  <dd className="text-2xs text-faint">
                    {data.trough ? fmtDateTime(data.trough.target_at) : '—'}</dd>
                </div>
                <AqiPill aqi={data.trough?.aqi ?? null} />
              </div>
            </dl>
          </div>
        </div>
      </div>

      {aqiReports.length > 0 && (
        <section className="mt-4">
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Model card</h2>
            <p className="mt-1 text-xs text-muted">
              Held-out performance from the most recent training run, measured on a
              chronological split. Skill is the improvement over a persistence
              baseline — "tomorrow will be like today" — which is the bar any
              forecaster has to clear to be worth deploying.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-line text-2xs uppercase
                                 tracking-wide text-faint">
                    <th scope="col" className="py-2 pr-4 font-medium">Horizon</th>
                    <th scope="col" className="py-2 pr-4 text-right font-medium">MAE</th>
                    <th scope="col" className="py-2 pr-4 text-right font-medium">
                      Persistence MAE</th>
                    <th scope="col" className="py-2 pr-4 text-right font-medium">Skill</th>
                    <th scope="col" className="py-2 pr-4 text-right font-medium">R²</th>
                    <th scope="col" className="py-2 text-right font-medium">Test rows</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {aqiReports.map((r) => (
                    <tr key={r.horizon_hours}>
                      <th scope="row" className="py-2 pr-4 font-medium text-ink">
                        {r.horizon_hours} h</th>
                      <td className="py-2 pr-4 text-right tnum text-muted">{r.mae}</td>
                      <td className="py-2 pr-4 text-right tnum text-muted">
                        {r.baseline_mae}</td>
                      <td className="py-2 pr-4 text-right tnum font-medium text-good">
                        {(r.skill_vs_persistence * 100).toFixed(0)}%</td>
                      <td className="py-2 pr-4 text-right tnum text-muted">{r.r2}</td>
                      <td className="py-2 text-right tnum text-muted">
                        {r.n_test.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {status.data?.data.demo_readings ? (
              <p className="mt-3 rounded-lg bg-raised px-3 py-2 text-2xs
                            leading-relaxed text-muted">
                <strong className="text-ink">Read these numbers carefully.</strong>{' '}
                {status.data.data.demo_readings.toLocaleString('en-IN')} of the
                training rows are AIRS-generated history rather than measurements.
                A model scored against its own generator looks better than it will
                on live data — real skill will be materially lower, and the model
                card will show it once live history accumulates.
              </p>
            ) : null}
          </div>
        </section>
      )}
    </>
  )
}
