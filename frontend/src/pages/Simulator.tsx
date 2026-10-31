import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { AqiGauge } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { ProvenanceBadge } from '@/components/Provenance'
import { CitySelector, StationSelector } from '@/components/Selectors'
import { CardSkeleton, ErrorState } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { ScenarioCompare } from '@/charts/ScenarioCompare'
import { SourceBreakdown } from '@/charts/SourceBreakdown'
import { api } from '@/lib/api'
import { compactNumber, num } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import type { SimulationResponse } from '@/lib/types'

export default function Simulator() {
  const { citySlug, stationId } = useSelection()
  const [levers, setLevers] = useState<Record<string, number>>({})
  const [result, setResult] = useState<SimulationResponse | null>(null)

  const interventions = useQuery({ queryKey: ['interventions'],
    queryFn: api.interventions, staleTime: 3_600_000 })
  const sources = useQuery({ queryKey: ['sources', citySlug, stationId],
    queryFn: () => api.sources(citySlug, stationId), enabled: Boolean(citySlug) })

  const run = useMutation({
    mutationFn: () => api.simulate({
      city_slug: citySlug, station_id: stationId,
      levers: Object.entries(levers)
        .filter(([, v]) => v > 0)
        .map(([key, magnitude]) => ({ key, magnitude })),
    }),
    onSuccess: setResult,
  })

  const active = useMemo(
    () => Object.entries(levers).filter(([, v]) => v > 0), [levers])

  return (
    <>
      <PageHeader
        title="Air Quality Intervention Simulator"
        description="Simulate potential air quality improvements under targeted policy interventions. Scenario estimates are computed from source-apportioned pollutant loads and atmospheric dispersion."
        actions={<><CitySelector /><StationSelector /></>}
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        {/* ── Controls ── */}
        <div className="grid content-start gap-4">
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Intervention controls</h2>
            <p className="mt-1 text-xs text-muted">
              Set how hard each lever is pulled. A lever with no matching source at
              this station will correctly show almost no benefit.
            </p>

            {interventions.isLoading ? (
              <div className="mt-4 space-y-4">
                {[0, 1, 2].map((i) => <div key={i} className="skeleton h-14 w-full" />)}
              </div>
            ) : interventions.isError ? (
              <ErrorState error={interventions.error} compact />
            ) : (
              <div className="mt-4 space-y-5">
                {interventions.data?.map((item) => {
                  const value = levers[item.key] ?? 0
                  return (
                    <div key={item.key}>
                      <div className="flex items-baseline justify-between gap-3">
                        <label htmlFor={`lever-${item.key}`}
                               className="text-xs font-medium text-ink">
                          {item.label}
                        </label>
                        <span className="text-xs font-semibold tnum text-brand">
                          {value}%
                        </span>
                      </div>
                      <input
                        id={`lever-${item.key}`} type="range" min={0}
                        max={item.max_magnitude} step={5} value={value}
                        onChange={(e) => setLevers((prev) => ({
                          ...prev, [item.key]: Number(e.target.value) }))}
                        className="mt-2 w-full accent-[rgb(var(--c-brand))]"
                        aria-describedby={`lever-desc-${item.key}`}
                      />
                      <p id={`lever-desc-${item.key}`}
                         className="mt-1 text-2xs leading-relaxed text-faint">
                        {item.description} Max {item.max_magnitude}% ·{' '}
                        takes effect in ~{item.lag_hours} h · {item.cost_band} cost.
                      </p>
                    </div>
                  )
                })}
              </div>
            )}

            <div className="mt-5 flex gap-2">
              <button type="button" onClick={() => run.mutate()}
                      disabled={!active.length || run.isPending}
                      className="btn-primary flex-1">
                {run.isPending ? 'Simulating…' : 'Run simulation'}
              </button>
              <button type="button"
                      onClick={() => { setLevers({}); setResult(null) }}
                      className="btn-ghost px-3">Reset</button>
            </div>
            {!active.length && (
              <p className="mt-2 text-2xs text-faint">
                Move at least one slider above zero.
              </p>
            )}
          </div>

          {sources.data && (
            <ChartFrame title="Current source mix"
                        subtitle="What the levers have to work with"
                        provenance={sources.data.provenance}>
              <SourceBreakdown contributions={sources.data.contributions}
                               confidence={sources.data.confidence} />
            </ChartFrame>
          )}
        </div>

        {/* ── Results ── */}
        <div className="grid content-start gap-4">
          {run.isError && (
            <ErrorState error={run.error} onRetry={() => run.mutate()} />
          )}

          {!result && !run.isPending && (
            <div className="card card-pad flex min-h-[320px] flex-col items-center
                            justify-center text-center">
              <p className="text-sm font-medium text-ink">
                No scenario simulated yet
              </p>
              <p className="mt-1.5 max-w-sm text-sm text-muted">
                Pull a lever on the left and run the simulation. AIRS will split the
                model-estimated pollution into source shares, apply the lever only to the
                share it can actually affect, discount it by how well the atmosphere
                is dispersing right now, and recompute the AQI from the resulting
                concentrations.
              </p>
            </div>
          )}

          {run.isPending && <CardSkeleton lines={6} />}

          {result && (
            <>
              <div className="card card-pad">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="text-sm font-semibold text-ink">
                      Air Quality Intervention Simulator — {result.station?.name}
                    </h2>
                    <p className="mt-0.5 text-2xs text-muted">
                      Receptor site baseline · Evaluates localized intervention impacts at this urban monitoring location
                    </p>
                  </div>
                  <ProvenanceBadge provenance={result.provenance} showSource={false} />
                </div>

                <div className="mt-4 grid gap-6 sm:grid-cols-[1fr_auto_1fr]
                                sm:items-center">
                  <div className="text-center">
                    <p className="label-eyebrow">Station Baseline</p>
                    <AqiGauge aqi={result.baseline.aqi} size={160}
                              label={result.provenance?.mode === 'demo' ? 'Receptor Baseline (Demo)' : 'Receptor Baseline'} />
                    <p className="mt-1 text-2xs text-faint">
                      Local urban receptor site
                    </p>
                  </div>
                  <div className="flex flex-col items-center justify-center">
                    <span aria-hidden="true"
                          className="text-2xl text-faint sm:rotate-0">→</span>
                    <span className={`mt-1 text-lg font-semibold tnum ${
                      (result.deltas.improvement_pct ?? 0) > 0
                        ? 'text-good' : 'text-muted'}`}>
                      {result.deltas.improvement_pct === null ? '—'
                        : `${result.deltas.improvement_pct > 0 ? '−' : '+'}${
                            Math.abs(result.deltas.improvement_pct)}%`}
                    </span>
                    <span className="text-2xs text-faint">AQI Change</span>
                  </div>
                  <div className="text-center">
                    <p className="label-eyebrow">Simulated Outcome</p>
                    <AqiGauge aqi={result.simulated.aqi} size={160}
                              label="Simulated AQI" />
                  </div>
                </div>

                <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 border-t
                               border-line pt-4 text-xs sm:grid-cols-4">
                  <div>
                    <dt className="text-faint">PM2.5 change</dt>
                    <dd className="mt-0.5 font-semibold tnum text-ink">
                      {num(result.deltas.pm25, 1)} µg/m³</dd>
                  </div>
                  <div>
                    <dt className="text-faint">PM10 change</dt>
                    <dd className="mt-0.5 font-semibold tnum text-ink">
                      {num(result.deltas.pm10, 1)} µg/m³</dd>
                  </div>
                  <div>
                    <dt className="text-faint">Band change</dt>
                    <dd className="mt-0.5 font-semibold text-ink">
                      {result.deltas.category_changed ? 'Yes' : 'No'}</dd>
                  </div>
                  <div>
                    <dt className="text-faint">People affected</dt>
                    <dd className="mt-0.5 font-semibold tnum text-ink">
                      {compactNumber(result.deltas.exposure?.population_exposed)}</dd>
                  </div>
                </dl>

                <p className="mt-4 rounded-lg bg-raised px-3 py-2.5 text-2xs
                              leading-relaxed text-muted">
                  <span className="font-semibold text-ink">Receptor site context: </span>
                  {result.caveat} Local station baselines reflect street-level urban emission density and microclimates, which can differ from regional background or CAMS atmospheric model grid averages. Confidence {Math.round(result.confidence * 100)}%, engine {result.engine_version}.
                </p>
              </div>

              <ChartFrame title="Pollutants after the intervention"
                          subtitle="Indexed to today = 100%, so pollutants on different units are comparable in one frame"
                          provenance={result.provenance}>
                <ScenarioCompare baseline={result.baseline.concentrations}
                                 simulated={result.simulated.concentrations} />
              </ChartFrame>

              <div className="card card-pad">
                <h2 className="text-sm font-semibold text-ink">
                  How each lever contributed
                </h2>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-line text-2xs uppercase
                                     tracking-wide text-faint">
                        <th scope="col" className="py-2 pr-3 font-medium">Lever</th>
                        <th scope="col" className="py-2 pr-3 text-right font-medium">
                          Magnitude</th>
                        <th scope="col" className="py-2 pr-3 text-right font-medium">
                          Source share it can affect</th>
                        <th scope="col" className="py-2 text-right font-medium">
                          PM2.5 cut</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {result.per_lever.map((lever) => (
                        <tr key={lever.key}>
                          <th scope="row" className="py-2 pr-3 font-medium text-ink">
                            {lever.label}</th>
                          <td className="py-2 pr-3 text-right tnum text-muted">
                            {lever.magnitude_pct}%</td>
                          <td className="py-2 pr-3 text-right tnum text-muted">
                            {lever.attributable_source_share_pct}%</td>
                          <td className="py-2 text-right tnum text-ink">
                            {num(lever.pollutant_reduction_pct.pm25, 1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {result.warnings.length > 0 && (
                  <ul className="mt-3 space-y-1.5">
                    {result.warnings.map((w) => (
                      <li key={w} className="rounded-lg bg-usg/10 px-2.5 py-2
                                             text-2xs text-usg">{w}</li>
                    ))}
                  </ul>
                )}

                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-brand">
                    Modelling assumptions
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {result.assumptions.map((a) => (
                      <li key={a} className="flex gap-2 text-2xs leading-relaxed
                                             text-muted">
                        <span aria-hidden="true" className="text-faint">—</span>{a}
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
