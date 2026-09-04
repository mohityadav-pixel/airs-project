import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { AqiGauge, AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { ProvenanceBadge } from '@/components/Provenance'
import { CitySelector, StationSelector } from '@/components/Selectors'
import { StatTile } from '@/components/StatTile'
import { CardSkeleton, ChartSkeleton, ErrorState } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { ForecastChart } from '@/charts/ForecastChart'
import { PollutantBars } from '@/charts/PollutantBars'
import { SourceBreakdown } from '@/charts/SourceBreakdown'
import { AirQualityMap, MapLegend } from '@/maps/AirQualityMap'
import { api } from '@/lib/api'
import { POLLUTANT_LABEL, SEVERITY_STYLE, ZONE_LABEL } from '@/lib/aqi'
import { compactNumber, num, relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import type { HealthAdvisory } from '@/lib/types'


/**
 * On a phone the citizen's second question — after "how bad is it?" — is "what
 * should I do?", so this card sits directly under the AQI dial on small
 * screens and moves to the analysis column on wide ones.
 */
function HealthCard({ advisory }: { advisory: HealthAdvisory | undefined }) {
  if (!advisory?.available) return null
  return (
    <div className="card card-pad order-1 lg:order-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-ink">Health guidance</h2>
          <p className="text-2xs text-faint">{advisory.group_label}</p>
        </div>
        <span className="chip capitalize">{advisory.risk_level} risk</span>
      </div>
      <dl className="grid gap-2.5 text-xs sm:grid-cols-2 lg:grid-cols-4">
        {([['Outdoors', advisory.outdoor_activity],
           ['Exercise', advisory.exercise],
           ['Mask', advisory.mask],
           ['Ventilation', advisory.ventilation]] as const).map(([label, value]) => (
          <div key={label}>
            <dt className="text-2xs font-medium uppercase tracking-wide text-faint">
              {label}</dt>
            <dd className="mt-0.5 leading-relaxed text-muted">{value}</dd>
          </div>
        ))}
      </dl>
      {advisory.notes?.length ? (
        <p className="mt-3 rounded-lg bg-raised px-2.5 py-2 text-2xs leading-relaxed
                      text-muted">{advisory.notes[0]}</p>
      ) : null}
      <p className="mt-3 border-t border-line pt-2.5 text-2xs text-faint">
        {advisory.disclaimer}
      </p>
    </div>
  )
}

export default function Dashboard() {
  const { citySlug, stationId, setStation, city } = useSelection()

  const current = useQuery({ queryKey: ['current', citySlug, stationId],
    queryFn: () => api.current(citySlug, stationId), enabled: Boolean(citySlug) })
  const summary = useQuery({ queryKey: ['summary', citySlug],
    queryFn: () => api.summary(citySlug), enabled: Boolean(citySlug) })
  const prediction = useQuery({ queryKey: ['prediction', citySlug, stationId],
    queryFn: () => api.predictions(citySlug, stationId, 24), enabled: Boolean(citySlug) })
  const sources = useQuery({ queryKey: ['sources', citySlug, stationId],
    queryFn: () => api.sources(citySlug, stationId), enabled: Boolean(citySlug) })
  const mapData = useQuery({ queryKey: ['map', citySlug],
    queryFn: () => api.map(citySlug), enabled: Boolean(citySlug) })
  const alerts = useQuery({ queryKey: ['alerts', citySlug],
    queryFn: () => api.alerts(citySlug), enabled: Boolean(citySlug) })
  const advisory = useQuery({ queryKey: ['advisory', citySlug, stationId],
    queryFn: () => api.healthAdvisory(citySlug, stationId), enabled: Boolean(citySlug) })
  const recommendations = useQuery({ queryKey: ['recommendations', citySlug],
    queryFn: () => api.recommendations(citySlug), enabled: Boolean(citySlug) })

  const aq = current.data
  const weather = aq?.weather

  return (
    <>
      <PageHeader
        title={city ? `${city.name} air quality` : 'Air quality'}
        description="Live readings, what is driving them, and what happens next."
        actions={<><CitySelector /><StationSelector /></>}
      />

      {/* ── Priority row: the citizen answer, above everything else ── */}
      <section className="grid gap-4 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <div className="card card-pad">
          {current.isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="skeleton h-40 w-40 rounded-full" />
            </div>
          ) : current.isError ? (
            <ErrorState error={current.error} onRetry={() => current.refetch()} compact />
          ) : aq ? (
            <>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">
                    {aq.station.name}
                  </p>
                  <p className="text-2xs text-faint">
                    {ZONE_LABEL[aq.station.zone_type] ?? aq.station.zone_type}
                    {' · '}{relativeTime(aq.observed_at)}
                  </p>
                </div>
                <ProvenanceBadge provenance={aq.provenance} showSource={false} />
              </div>

              <div className="mt-3">
                <AqiGauge aqi={aq.aqi} trend={aq.trend_1h} />
              </div>

              {aq.category?.advice && (
                <p className="mt-3 rounded-xl bg-raised px-3 py-2.5 text-xs
                              leading-relaxed text-muted">
                  {aq.category.advice}
                </p>
              )}

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t
                             border-line pt-3.5 text-xs">
                <dt className="text-faint">Driver</dt>
                <dd className="text-right font-medium text-ink">
                  {aq.dominant_pollutant
                    ? POLLUTANT_LABEL[aq.dominant_pollutant] ?? aq.dominant_pollutant
                    : '—'}</dd>
                <dt className="text-faint">Wind</dt>
                <dd className="text-right tnum text-muted">
                  {num(weather?.wind_speed_mps, 1)} m/s</dd>
                <dt className="text-faint">Temp</dt>
                <dd className="text-right tnum text-muted">
                  {num(weather?.temperature_c, 1)} °C</dd>
                <dt className="text-faint">Humidity</dt>
                <dd className="text-right tnum text-muted">
                  {num(weather?.humidity_pct, 0)}%</dd>
                <dt className="text-faint">Ventilation</dt>
                <dd className="text-right tnum text-muted">
                  {num(weather?.ventilation_index, 2)}</dd>
                <dt className="text-faint">Congestion</dt>
                <dd className="text-right tnum text-muted">
                  {num(aq.traffic?.congestion_index, 2)}</dd>
              </dl>
            </>
          ) : null}
        </div>

        <div className="grid content-start gap-4">
          <HealthCard advisory={advisory.data} />

          <div className="order-2 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="City average"
              value={summary.data ? num(summary.data.average_aqi, 0) : '—'}
              unit="AQI"
              footnote={summary.data
                ? `${summary.data.reporting_stations} of ${summary.data.station_count} stations reporting`
                : undefined} />
            <StatTile label="Worst station"
              value={summary.data ? num(summary.data.worst_aqi, 0) : '—'}
              unit="AQI"
              footnote={summary.data?.worst_station?.name} />
            <StatTile label="Forecast peak (24 h)"
              value={prediction.data?.peak ? num(prediction.data.peak.aqi, 0) : '—'}
              unit="AQI"
              delta={prediction.data?.peak && aq?.aqi != null
                ? `${prediction.data.peak.aqi! > aq.aqi ? '▲' : '▼'} ${
                    num(Math.abs(prediction.data.peak.aqi! - aq.aqi), 0)} vs now`
                : undefined}
              deltaTone={prediction.data?.peak && aq?.aqi != null
                ? (prediction.data.peak.aqi! > aq.aqi ? 'bad' : 'good') : 'neutral'}
              footnote="ML forecast" />
            <StatTile label="Hotspots"
              value={summary.data ? summary.data.hotspot_station_ids.length : '—'}
              footnote={summary.data
                ? `Stations at ≥1.25× the city median`
                : undefined} />
          </div>

          {alerts.data && alerts.data.length > 0 && (
            <div className="card card-pad order-3">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-ink">Active alerts</h2>
                <span className="chip">{alerts.data.length}</span>
              </div>
              <ul className="divide-y divide-line">
                {alerts.data.slice(0, 4).map((alert) => (
                  <li key={alert.id} className="flex gap-3 py-2.5 first:pt-0 last:pb-0">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                          aria-hidden="true"
                          style={{ backgroundColor: SEVERITY_STYLE[alert.severity]?.dot }} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink">{alert.title}</p>
                      <p className="mt-0.5 text-xs text-muted">{alert.what_happened}</p>
                      <p className="mt-1 text-2xs text-faint">
                        <span className="font-medium">Do:</span> {alert.recommended_action}
                      </p>
                    </div>
                    <span className="ml-auto shrink-0 text-2xs uppercase tracking-wide
                                     text-faint">
                      {SEVERITY_STYLE[alert.severity]?.label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {prediction.data?.explanation && (
            <div className="card card-pad order-4 lg:order-3">
              <div className="mb-2 flex items-start justify-between gap-3">
                <h2 className="text-sm font-semibold text-ink">
                  {prediction.data.explanation.headline}
                </h2>
                <ProvenanceBadge provenance={prediction.data.provenance}
                                 showSource={false} />
              </div>
              <p className="text-sm leading-relaxed text-muted">
                {prediction.data.explanation.simple}
              </p>
              {prediction.data.explanation.factors.length > 0 && (
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {prediction.data.explanation.factors.map((f) => (
                    <li key={f} className="chip">{f}</li>
                  ))}
                </ul>
              )}
              <details className="mt-3 text-xs">
                <summary className="cursor-pointer text-brand">
                  Technical explanation
                </summary>
                <p className="mt-2 leading-relaxed text-muted">
                  {prediction.data.explanation.technical}
                </p>
                <p className="mt-2 text-2xs text-faint">
                  Generated by the {prediction.data.explanation.tier === 'llm'
                    ? 'language model from AIRS data'
                    : 'deterministic explanation engine'}.
                </p>
              </details>
            </div>
          )}
        </div>
      </section>

      {/* ── Analysis row ── */}
      <section className="mt-4 grid gap-4 lg:grid-cols-3">
        {prediction.isLoading ? <ChartSkeleton /> : prediction.data ? (
          <div className="lg:col-span-2">
            <ChartFrame
              title="Next 24 hours"
              subtitle={`Issued ${relativeTime(prediction.data.issued_at)} · ${
                String((prediction.data.model as { tier?: string }).tier ?? '')} tier`}
              provenance={prediction.data.provenance}
              footnote="The band is the 80% prediction interval — the model's own
                        uncertainty, not a best/worst case.">
              <ForecastChart curve={prediction.data.curve}
                             currentAqi={prediction.data.current_aqi} />
            </ChartFrame>
          </div>
        ) : null}

        {sources.isLoading ? <CardSkeleton lines={6} /> : sources.data ? (
          <ChartFrame title="Likely pollution sources"
                      subtitle={sources.data.station.name}
                      provenance={sources.data.provenance}>
            <SourceBreakdown contributions={sources.data.contributions}
                             confidence={sources.data.confidence} />
            {sources.data.evidence.length > 0 && (
              <details className="mt-3 text-xs">
                <summary className="cursor-pointer text-brand">
                  Why AIRS thinks this
                </summary>
                <ul className="mt-2 space-y-2">
                  {sources.data.evidence.map((e, i) => (
                    <li key={i} className="rounded-lg bg-raised px-2.5 py-2">
                      <p className="text-2xs font-medium text-ink">
                        {e.signal} = {String(e.value)}
                      </p>
                      <p className="mt-0.5 text-2xs leading-relaxed text-muted">
                        {e.reading}
                      </p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </ChartFrame>
        ) : null}
      </section>

      <section className="mt-4">
        {aq && aq.pollutants.length > 0 && (
          <div>
            <ChartFrame title="Pollutants, compared on AQI sub-index"
                        subtitle="The only scale on which µg/m³ and ppb are comparable"
                        provenance={aq.provenance}>
              <PollutantBars pollutants={aq.pollutants} />
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <caption className="sr-only">
                    Pollutant concentrations and AQI sub-indices
                  </caption>
                  <thead>
                    <tr className="border-b border-line text-2xs uppercase
                                   tracking-wide text-faint">
                      <th scope="col" className="py-1.5 pr-3 font-medium">Pollutant</th>
                      <th scope="col" className="py-1.5 pr-3 text-right font-medium">
                        Concentration</th>
                      <th scope="col" className="py-1.5 pr-3 text-right font-medium">
                        Sub-index</th>
                      <th scope="col" className="py-1.5 text-right font-medium">
                        Share of AQI</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {aq.pollutants.map((p) => (
                      <tr key={p.key}>
                        <th scope="row" className="py-1.5 pr-3 font-medium text-ink">
                          {p.label}</th>
                        <td className="py-1.5 pr-3 text-right tnum text-muted">
                          {num(p.concentration, 1)} {p.unit}</td>
                        <td className="py-1.5 pr-3 text-right">
                          <AqiPill aqi={p.sub_index} size="sm" /></td>
                        <td className="py-1.5 text-right tnum text-muted">
                          {p.share_of_aqi === null ? '—' : `${num(p.share_of_aqi, 0)}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartFrame>
          </div>
        )}

      </section>

      {/* ── Map + actions ── */}
      <section className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {mapData.isLoading ? <ChartSkeleton height={420} />
            : mapData.isError ? <ErrorState error={mapData.error} />
            : mapData.data ? (
              <ChartFrame title="Station map"
                          subtitle="Click a station to focus the whole dashboard on it"
                          provenance={mapData.data.provenance}
                          actions={<Link to="/map"
                                         className="btn-subtle px-2.5 py-1 text-xs">
                                     Full map
                                   </Link>}>
                <AirQualityMap city={mapData.data.city} points={mapData.data.points}
                               selectedId={stationId} onSelect={setStation}
                               height={420} />
                <div className="mt-3">
                  <MapLegend categories={mapData.data.legend} />
                </div>
              </ChartFrame>
            ) : null}
        </div>

        <div className="card card-pad">
          <div className="mb-3 flex items-start justify-between gap-2">
            <h2 className="text-sm font-semibold text-ink">Recommended actions</h2>
            {recommendations.data && (
              <ProvenanceBadge provenance={recommendations.data.provenance}
                               showSource={false} />
            )}
          </div>
          {recommendations.isLoading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => <div key={i} className="skeleton h-16 w-full" />)}
            </div>
          ) : recommendations.data?.immediate.length ? (
            <ul className="space-y-3">
              {recommendations.data.immediate.slice(0, 3).map((rec, i) => (
                <li key={i} className="rounded-xl border border-line bg-raised p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-semibold text-ink">{rec.action}</p>
                    <span className="shrink-0 rounded-md bg-brand/10 px-1.5 py-0.5
                                     text-2xs font-semibold tnum text-brand"
                          title={`Priority score ${Math.round(rec.priority_score)} of 100`}>
                      {num(rec.priority_score, 0)}
                    </span>
                  </div>
                  <p className="mt-1.5 text-2xs leading-relaxed text-muted">
                    {rec.reason}
                  </p>
                  <p className="mt-1.5 text-2xs text-faint">{rec.expected_impact}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted">
              No immediate interventions are indicated for this city right now.
            </p>
          )}
          <Link to="/simulator"
                className="btn-ghost mt-3 w-full px-3 py-2 text-xs">
            Simulate an intervention
          </Link>
        </div>
      </section>

      {summary.data && (
        <p className="mt-5 text-2xs text-faint">
          {compactNumber(city?.population)} residents ·{' '}
          {summary.data.dominant_pollutant
            ? POLLUTANT_LABEL[summary.data.dominant_pollutant]
              ?? summary.data.dominant_pollutant
            : 'No pollutant'} is the most
          common driver across reporting stations · updated{' '}
          {relativeTime(summary.data.updated_at)}.
        </p>
      )}
    </>
  )
}
