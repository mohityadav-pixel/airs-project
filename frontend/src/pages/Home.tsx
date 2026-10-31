import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { CardSkeleton } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { PollutantBars } from '@/charts/PollutantBars'
import { SourceBreakdown } from '@/charts/SourceBreakdown'
import { api } from '@/lib/api'
import { num } from '@/lib/format'
import { useSelection } from '@/lib/selection'

import { PollutantsSection } from './home/AirNow'
import { ForecastSection } from './home/ForecastSection'
import { HistorySection } from './home/HistorySection'
import { IndiaSection } from './home/IndiaSection'
import { LiveHero, useLive } from './home/LiveHero'
import { StationsSection } from './home/StationsSection'
import { Section } from './home/shared'

/* ── 4. why ─────────────────────────────────────────────────────────── */

function WhySection() {
  const { citySlug, stationId } = useSelection()
  const live = useLive()
  const sources = useQuery({ queryKey: ['sources', citySlug, stationId],
    queryFn: () => api.sources(citySlug, stationId), enabled: Boolean(citySlug) })
  const prediction = useQuery({ queryKey: ['prediction', citySlug, stationId, 24],
    queryFn: () => api.predictions(citySlug, stationId, 24),
    enabled: Boolean(citySlug) })
  const current = useQuery({ queryKey: ['current', citySlug, stationId],
    queryFn: () => api.current(citySlug, stationId), enabled: Boolean(citySlug) })

  return (
    <Section id="why" eyebrow="Source Apportionment" title="Pollution Drivers & Emission Sources"
             lede="AIRS analyzes pollutant ratios, local meteorology, and urban emission
                   factors to determine what produces the air quality at key monitoring stations."
             tint>
      {current.data && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface/90 px-4 py-3 text-xs shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-brand/15 px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider text-brand">
              Receptor Analysis
            </span>
            <span className="font-semibold text-ink">
              Monitoring Station: {current.data.station?.name ?? 'Local Station'}
            </span>
            {current.data.station?.zone_type && (
              <span className="rounded bg-raised px-1.5 py-0.5 text-2xs text-muted">
                {current.data.station.zone_type.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-2xs text-muted">
            <span>Station AQI: <strong className="font-bold text-ink">{current.data.aqi ?? '—'}</strong></span>
            {live.data?.aqi != null && (
              <span className="text-faint">
                · City-wide aggregate: <strong className="font-semibold text-muted">{live.data.aqi}</strong>
                {current.data.aqi != null && Math.abs(current.data.aqi - live.data.aqi) >= 10 && (
                  <span className="ml-1 text-2xs font-medium text-brand">
                    ({current.data.aqi > live.data.aqi ? 'micro-climate hotspot' : 'cleaner sector'})
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {sources.isLoading ? <CardSkeleton lines={7} /> : sources.data ? (
          <ChartFrame title={`Where the pollution is coming from — ${sources.data.station?.name ?? 'Station'}`}
                      subtitle="Estimated share of pollutant load based on stoichiometry & meteorology"
                      provenance={sources.data.provenance}>
            <SourceBreakdown contributions={sources.data.contributions}
                             confidence={sources.data.confidence} />
          </ChartFrame>
        ) : null}

        <div className="grid content-start gap-4">
          {prediction.data?.explanation && (
            <div className="card card-pad">
              <h3 className="text-sm font-bold text-ink">
                {prediction.data.explanation.headline}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {prediction.data.explanation.simple}
              </p>
              {prediction.data.explanation.factors.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {prediction.data.explanation.factors.map((f) => (
                    <li key={f} className="flex gap-2 text-xs text-muted">
                      <span aria-hidden="true" className="mt-1 h-1.5 w-1.5 shrink-0
                                                          rounded-full bg-brand" />
                      {f}
                    </li>
                  ))}
                </ul>
              )}
              <details className="mt-3">
                <summary className="cursor-pointer text-xs font-semibold text-brand">
                  The technical version
                </summary>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {prediction.data.explanation.technical}
                </p>
              </details>
            </div>
          )}

          {sources.data && sources.data.evidence.length > 0 && (
            <div className="card card-pad">
              <h3 className="text-sm font-bold text-ink">The evidence</h3>
              <ul className="mt-3 space-y-2.5">
                {sources.data.evidence.slice(0, 5).map((e, i) => (
                  <li key={i} className="rounded-xl bg-raised px-3 py-2.5">
                    <p className="text-2xs font-bold text-brand">
                      {e.signal} = {String(e.value)}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted">
                      {e.reading}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {current.data && current.data.pollutants.length > 0 && (
        <div className="mt-4">
          <ChartFrame title={`Which pollutant is driving the number (${current.data.station?.name ?? 'Station'})`}
                      subtitle={`Sub-indices for ${current.data.station?.name ?? 'station'} (AQI ${current.data.aqi ?? '—'}) compared on the AQI sub-index scale`}
                      provenance={current.data.provenance}>
            <PollutantBars pollutants={current.data.pollutants} height={220} />
          </ChartFrame>
        </div>
      )}
    </Section>
  )
}

/* ── 5. what can be done ────────────────────────────────────────────── */

const CITIZEN_ACTIONS = [
  { title: 'Time your day around the air',
    body: 'Early afternoon is usually the cleanest window; the two commute peaks and '
        + 'the hours after sunset are the worst. Shift walks, runs and errands into '
        + 'the clean window and you cut your dose without changing anything else.' },
  { title: 'Make one clean room at home',
    body: 'Close the windows during peaks, ventilate at midday, and if you have a '
        + 'purifier run it in the room you sleep in. Indoor air follows outdoor air '
        + 'within an hour or two, so the timing matters as much as the filter.' },
  { title: 'A real mask, not a cloth one',
    body: 'When PM2.5 is the driver, a well-fitted N95 or FFP2 helps and a cloth or '
        + 'surgical mask does very little. When ozone is the driver, no mask helps — '
        + 'changing the time of day does.' },
  { title: 'Protect skin and eyes',
    body: 'Particulate settles on skin and drives oxidative stress. Rinse your face '
        + 'and eyes after a long time outside, keep the skin barrier moisturised, and '
        + 'use sunscreen — pollution and UV compound each other.' },
]

function ActionSection() {
  const { citySlug } = useSelection()
  const recommendations = useQuery({ queryKey: ['recommendations', citySlug],
    queryFn: () => api.recommendations(citySlug), enabled: Boolean(citySlug) })

  const cityActions = [
    ...(recommendations.data?.immediate ?? []),
    ...(recommendations.data?.short_term ?? []),
  ].slice(0, 4)

  return (
    <Section id="solutions" eyebrow="Action & Solutions" title="Targeted Interventions & Recommendations"
             lede="Evidence-based policy and citizen actions: what residents can do
                   today, and policy levers required to reduce pollution levels.">
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-ink">
            <span className="flex h-6 w-6 items-center justify-center rounded-full
                             bg-brand-soft text-2xs font-bold text-brand">You</span>
            Protect yourself today
          </h3>
          <ul className="space-y-2.5">
            {CITIZEN_ACTIONS.map((action) => (
              <li key={action.title} className="card card-pad">
                <p className="text-sm font-bold text-ink">{action.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  {action.body}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-ink">
            <span className="flex h-6 w-6 items-center justify-center rounded-full
                             bg-accent-soft text-2xs font-bold text-accent">City</span>
            What would move the number here
          </h3>
          {recommendations.isLoading ? <CardSkeleton lines={6} />
            : cityActions.length ? (
              <ul className="space-y-2.5">
                {cityActions.map((rec, i) => (
                  <li key={i} className="card card-pad">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-bold text-ink">{rec.action}</p>
                      <span className="shrink-0 rounded-full bg-accent-soft px-2
                                       py-0.5 text-2xs font-bold tnum text-accent"
                            title="Priority score out of 100">
                        {num(rec.priority_score, 0)}
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-muted">
                      {rec.reason}
                    </p>
                    <p className="mt-1.5 text-2xs leading-relaxed text-faint">
                      {rec.expected_impact}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="card card-pad text-sm text-muted">
                No intervention is indicated for this city right now — the air is
                within a range where local action would not measurably change it.
              </div>
            )}

          <div className="mt-3 rounded-2xl border border-dashed border-brand/40
                          bg-brand-soft/40 p-4">
            <p className="text-xs leading-relaxed text-muted">
              Want to test one of these before committing to it? The{' '}
              <Link to="/simulator" className="font-semibold text-brand underline
                                               underline-offset-2">
                Air Quality Intervention Simulator
              </Link>{' '}models what a policy intervention would achieve here — applied
              only to the share of pollution that source is actually responsible for.
            </p>
          </div>
        </div>
      </div>
    </Section>
  )
}

/* ── page ───────────────────────────────────────────────────────────── */

export default function Home() {
  return (
    <>
      <LiveHero />
      <PollutantsSection />
      <ForecastSection />
      <StationsSection />
      <HistorySection />
      <WhySection />
      <ActionSection />
      <IndiaSection />
    </>
  )
}
