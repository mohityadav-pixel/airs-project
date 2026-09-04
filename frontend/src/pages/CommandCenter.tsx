import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { AqiPill } from '@/components/AqiGauge'
import { PageHeader } from '@/components/PageHeader'
import { CitySelector } from '@/components/Selectors'
import { StatTile } from '@/components/StatTile'
import { CardSkeleton, ErrorState } from '@/components/State'
import { api } from '@/lib/api'
import { SEVERITY_STYLE, ZONE_LABEL } from '@/lib/aqi'
import { compactNumber, num, relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import type { CommandCenterZone } from '@/lib/types'

function PriorityBar({ score }: { score: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
        <span className="block h-full rounded-full bg-brand"
              style={{ width: `${Math.min(score, 100)}%` }} />
      </span>
      <span className="w-8 text-right text-xs font-semibold tnum text-ink">
        {num(score, 0)}
      </span>
    </span>
  )
}

function ZoneDetail({ zone, onClose }:
  { zone: CommandCenterZone; onClose: () => void }) {
  return (
    <div className="card card-pad">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{zone.station.name}</h3>
          <p className="text-2xs text-faint">
            {ZONE_LABEL[zone.station.zone_type] ?? zone.station.zone_type} ·{' '}
            {compactNumber(zone.station.population_exposed)} exposed ·{' '}
            {relativeTime(zone.observed_at)}
          </p>
        </div>
        <button type="button" onClick={onClose}
                className="btn-subtle px-2 py-1 text-xs">Close</button>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-xs sm:grid-cols-4">
        <div><dt className="text-faint">Now</dt>
          <dd className="mt-0.5"><AqiPill aqi={zone.aqi} /></dd></div>
        <div><dt className="text-faint">Predicted peak</dt>
          <dd className="mt-0.5"><AqiPill aqi={zone.predicted_peak_aqi} /></dd></div>
        <div><dt className="text-faint">Dominant source</dt>
          <dd className="mt-1 font-medium text-ink">
            {zone.top_source_label ?? '—'}</dd></div>
        <div><dt className="text-faint">Best lever</dt>
          <dd className="mt-1 font-medium text-ink">{zone.best_lever ?? '—'}</dd></div>
      </dl>

      <h4 className="mt-5 text-2xs font-semibold uppercase tracking-wide text-faint">
        How the priority score was built
      </h4>
      <p className="mt-1 text-2xs leading-relaxed text-muted">
        {zone.priority_rationale}
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line text-2xs uppercase tracking-wide
                           text-faint">
              <th scope="col" className="py-2 pr-3 font-medium">Factor</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">Raw</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">
                Normalised</th>
              <th scope="col" className="py-2 pr-3 text-right font-medium">Weight</th>
              <th scope="col" className="py-2 font-medium">Meaning</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {Object.entries(zone.priority_factors).map(([key, f]) => (
              <tr key={key}>
                <th scope="row" className="py-2 pr-3 font-medium capitalize text-ink">
                  {key.replace(/_/g, ' ')}</th>
                <td className="py-2 pr-3 text-right tnum text-muted">
                  {f.raw === null || f.raw === undefined ? '—' : num(f.raw, 0)}</td>
                <td className="py-2 pr-3 text-right tnum text-muted">
                  {f.value === null ? '—' : f.value.toFixed(2)}</td>
                <td className="py-2 pr-3 text-right tnum text-muted">{f.weight}</td>
                <td className="py-2 text-muted">{f.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Link to="/simulator" className="btn-ghost mt-4 px-3 py-2 text-xs">
        Simulate an intervention here
      </Link>
    </div>
  )
}

export default function CommandCenter() {
  const { citySlug } = useSelection()
  const [selected, setSelected] = useState<CommandCenterZone | null>(null)

  const cc = useQuery({ queryKey: ['command-center', citySlug],
    queryFn: () => api.commandCenter(citySlug), enabled: Boolean(citySlug),
    refetchInterval: 5 * 60 * 1000 })
  const recommendations = useQuery({ queryKey: ['recommendations', citySlug],
    queryFn: () => api.recommendations(citySlug), enabled: Boolean(citySlug) })

  if (cc.isLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => <CardSkeleton key={i} lines={4} />)}
      </div>
    )
  }
  if (cc.isError) return <ErrorState error={cc.error} onRetry={() => cc.refetch()} />
  const data = cc.data
  if (!data) return null

  return (
    <>
      <PageHeader title="City Command Center"
                  description="Operational view: where the city stands, what is about to get worse, and which lever buys the most."
                  actions={<CitySelector />}>
        <p className="mt-1.5 text-2xs text-faint">
          Refreshed {relativeTime(data.generated_at)} · auto-updates every 5 minutes
        </p>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <StatTile label="City average" value={num(data.headline.average_aqi, 0)}
                  unit="AQI"
                  footnote={`${data.headline.stations_reporting}/${data.headline.stations_total} reporting`} />
        <StatTile label="Worst station" value={num(data.headline.worst_aqi, 0)}
                  unit="AQI" deltaTone="bad" />
        <StatTile label="Hotspots" value={data.headline.hotspot_count}
                  footnote={`${compactNumber(data.headline.population_in_hotspots)} people exposed`} />
        <StatTile label="Deteriorating" value={data.headline.deteriorating_count}
                  footnote="Forecast to rise ≥15 AQI"
                  deltaTone={data.headline.deteriorating_count > 0 ? 'bad' : 'good'} />
        <StatTile label="Active alerts" value={data.headline.active_alerts} />
      </div>

      {selected && (
        <div className="mt-4">
          <ZoneDetail zone={selected} onClose={() => setSelected(null)} />
        </div>
      )}

      <section className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="card overflow-hidden lg:col-span-2">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-sm font-semibold text-ink">
              Zones by intervention priority
            </h2>
            <p className="text-2xs text-faint">
              {data.methodology.priority} Select a row for the full breakdown.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead>
                <tr className="border-b border-line text-2xs uppercase tracking-wide
                               text-faint">
                  <th scope="col" className="py-2.5 pl-4 pr-3 font-medium">Zone</th>
                  <th scope="col" className="py-2.5 pr-3 text-right font-medium">Now</th>
                  <th scope="col" className="py-2.5 pr-3 text-right font-medium">
                    Peak</th>
                  <th scope="col" className="py-2.5 pr-3 font-medium">
                    Dominant source</th>
                  <th scope="col" className="py-2.5 pr-3 font-medium">Best lever</th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.zones.map((zone) => (
                  <tr key={zone.station.id}
                      onClick={() => setSelected(zone)}
                      className="cursor-pointer hover:bg-raised">
                    <th scope="row" className="py-2.5 pl-4 pr-3 font-medium text-ink">
                      <span className="flex items-center gap-1.5">
                        {zone.station.name}
                        {zone.is_hotspot && (
                          <span className="rounded bg-unhealthy/15 px-1 py-px
                                           text-[9px] font-semibold uppercase
                                           text-unhealthy">hot</span>
                        )}
                      </span>
                      <span className="block text-2xs font-normal text-faint">
                        {compactNumber(zone.station.population_exposed)} exposed
                      </span>
                    </th>
                    <td className="py-2.5 pr-3 text-right">
                      <AqiPill aqi={zone.aqi} size="sm" /></td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="inline-flex flex-col items-end">
                        <AqiPill aqi={zone.predicted_peak_aqi} size="sm" />
                        {zone.expected_change !== null && (
                          <span className={`mt-0.5 text-2xs tnum ${
                            zone.expected_change > 0 ? 'text-unhealthy' : 'text-good'}`}>
                            {zone.expected_change > 0 ? '+' : ''}
                            {num(zone.expected_change, 0)}
                            {zone.hours_to_peak ? ` in ${zone.hours_to_peak}h` : ''}
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-muted">
                      {zone.top_source_label ?? '—'}
                      {zone.source_confidence !== null && (
                        <span className="block text-2xs text-faint">
                          {Math.round((zone.source_confidence ?? 0) * 100)}% confidence
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-3 text-muted">
                      {zone.best_lever ?? '—'}
                      {zone.best_lever_improvement_pct !== null && (
                        <span className="block text-2xs text-faint">
                          −{num(zone.best_lever_improvement_pct, 1)}% modelled
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-4">
                      <PriorityBar score={zone.priority_score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid content-start gap-4">
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">Active alerts</h2>
            {data.alerts.length === 0 ? (
              <p className="mt-2 text-xs text-muted">
                No active alerts in this city right now.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-line">
                {data.alerts.map((alert) => (
                  <li key={alert.id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" aria-hidden="true"
                            style={{ backgroundColor: SEVERITY_STYLE[alert.severity]?.dot }} />
                      <p className="text-xs font-semibold text-ink">{alert.title}</p>
                    </div>
                    <p className="mt-1 text-2xs leading-relaxed text-muted">
                      {alert.what_happened}
                    </p>
                    <p className="mt-1 text-2xs leading-relaxed text-faint">
                      {alert.why_it_matters}
                    </p>
                    <p className="mt-1.5 rounded-lg bg-raised px-2 py-1.5 text-2xs
                                  text-muted">
                      <span className="font-medium text-ink">Action:</span>{' '}
                      {alert.recommended_action}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {recommendations.data && (
        <section className="mt-4">
          <div className="card card-pad">
            <h2 className="text-sm font-semibold text-ink">
              Recommended interventions
            </h2>
            <p className="mt-1 text-xs text-muted">
              {recommendations.data.methodology.selection}{' '}
              {recommendations.data.methodology.impact}
            </p>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              {([['immediate', 'Immediate'], ['short_term', 'Short term'],
                 ['long_term', 'Long term']] as const).map(([key, label]) => (
                <div key={key}>
                  <h3 className="label-eyebrow">{label}</h3>
                  <ul className="mt-2 space-y-2.5">
                    {recommendations.data![key].length === 0 && (
                      <li className="text-xs text-faint">Nothing indicated.</li>
                    )}
                    {recommendations.data![key].map((rec, i) => (
                      <li key={i} className="rounded-xl border border-line bg-raised p-3">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-semibold text-ink">{rec.action}</p>
                          {rec.time_horizon !== 'long' && (
                            <span className="shrink-0 rounded-md bg-brand/10 px-1.5
                                             py-0.5 text-2xs font-semibold tnum
                                             text-brand">
                              {num(rec.priority_score, 0)}
                            </span>
                          )}
                        </div>
                        <p className="mt-1.5 text-2xs leading-relaxed text-muted">
                          {rec.reason}
                        </p>
                        <p className="mt-1.5 text-2xs leading-relaxed text-faint">
                          {rec.expected_impact}
                        </p>
                        <p className="mt-1.5 text-2xs text-faint">
                          Confidence {Math.round(rec.confidence * 100)}%
                          {rec.station_name ? ` · ${rec.station_name}` : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="mt-4 border-t border-line pt-3 text-2xs text-faint">
              {recommendations.data.methodology.limits}
            </p>
          </div>
        </section>
      )}
    </>
  )
}
