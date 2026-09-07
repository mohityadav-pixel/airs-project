import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { AqiGauge, AqiPill } from '@/components/AqiGauge'
import { CitySearch } from '@/components/CitySearch'
import { ProvenanceBadge } from '@/components/Provenance'
import { CardSkeleton, ChartSkeleton, ErrorState } from '@/components/State'
import { ChartFrame } from '@/charts/ChartFrame'
import { ForecastChart } from '@/charts/ForecastChart'
import { PollutantBars } from '@/charts/PollutantBars'
import { SourceBreakdown } from '@/charts/SourceBreakdown'
import { TrendChart } from '@/charts/TrendChart'
import { HourProfile } from '@/charts/HourProfile'
import { IndiaMap, ZONE_BANDS, ZoneLegend } from '@/maps/IndiaMap'
import { api } from '@/lib/api'
import { aqiColor, POLLUTANT_LABEL } from '@/lib/aqi'
import { fmtDateTime, num, relativeTime } from '@/lib/format'
import { useSelection } from '@/lib/selection'
import { useState } from 'react'
import type { SeriesPoint } from '@/lib/types'

/* ── section chrome ─────────────────────────────────────────────────── */

function Section({ id, eyebrow, title, lede, children, tint = false }: {
  id: string
  eyebrow: string
  title: string
  lede?: string
  children: React.ReactNode
  tint?: boolean
}) {
  return (
    <section id={id} className={tint ? 'bg-raised/60' : ''}>
      <div className="mx-auto max-w-content px-4 py-12 sm:px-6 sm:py-14">
        <header className="mb-6">
          <p className="label-eyebrow text-brand">{eyebrow}</p>
          <h2 className="section-title mt-1.5">{title}</h2>
          {lede && <p className="section-lede">{lede}</p>}
        </header>
        {children}
      </div>
    </section>
  )
}

/* ── 1. hero + city picker + live AQI ───────────────────────────────── */

function Hero() {
  const { citySlug, city } = useSelection()
  const current = useQuery({ queryKey: ['current', citySlug, undefined],
    queryFn: () => api.current(citySlug), enabled: Boolean(citySlug) })
  const summary = useQuery({ queryKey: ['summary', citySlug],
    queryFn: () => api.summary(citySlug), enabled: Boolean(citySlug) })
  const advisory = useQuery({ queryKey: ['advisory', citySlug, undefined],
    queryFn: () => api.healthAdvisory(citySlug), enabled: Boolean(citySlug) })

  const aq = current.data
  const tint = aq?.aqi != null ? aqiColor(aq.aqi) : '#C2410C'

  return (
    <section id="live" className="relative overflow-hidden">
      {/* The page's mood follows the air: the wash behind the hero is tinted by
          the current AQI band, so the state is legible before a word is read. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -top-24"
           style={{ background:
             `radial-gradient(58% 55% at 50% 22%, ${tint}22, transparent 72%)` }} />

      <div className="relative mx-auto max-w-content px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center
                        sm:justify-between">
          <div>
            <p className="label-eyebrow text-brand">Live air quality · India</p>
            <h1 className="mt-1.5 text-2xl font-extrabold tracking-tight text-ink
                           sm:text-3xl">
              How is the air where you are?
            </h1>
          </div>
          <CitySearch />
        </div>

        {current.isError && (
          <div className="mt-6">
            <ErrorState error={current.error} onRetry={() => current.refetch()} />
          </div>
        )}

        {current.isLoading && (
          <div className="mt-7 grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
            <CardSkeleton lines={5} /><CardSkeleton lines={7} />
          </div>
        )}

        {aq && (
          <div className="mt-7 grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
            {/* headline dial */}
            <div className="card card-pad flex flex-col items-center self-start">
              <div className="mb-1 flex w-full items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-ink">
                    {city?.name}
                  </p>
                  <p className="text-2xs text-faint">
                    {aq.station.name} · {relativeTime(aq.observed_at)}
                  </p>
                </div>
                <ProvenanceBadge provenance={aq.provenance} showSource={false} />
              </div>
              <AqiGauge aqi={aq.aqi} trend={aq.trend_1h} />
              {aq.category?.advice && (
                <p className="mt-3 w-full rounded-xl bg-raised px-3 py-2.5 text-xs
                              leading-relaxed text-muted">
                  {aq.category.advice}
                </p>
              )}

              {/* Where this reading sits on the whole scale. A number on its own
                  means little; the ladder gives it somewhere to stand. */}
              <div className="mt-4 w-full border-t border-line pt-3.5">
                <div className="flex h-2 w-full overflow-hidden rounded-full">
                  {ZONE_BANDS.map((band) => (
                    <span key={band.key} className="flex-1"
                          title={`${band.plain} — AQI ${band.range}`}
                          style={{ backgroundColor: band.color,
                                   opacity: aq.category?.key === band.key ? 1 : 0.3,
                                   boxShadow: 'inset -1.5px 0 0 rgb(var(--c-surface))' }} />
                  ))}
                </div>
                <div className="mt-1.5 flex justify-between text-[10px] tnum
                                text-faint">
                  <span>0</span><span>50</span><span>100</span><span>150</span>
                  <span>200</span><span>300+</span>
                </div>
                <p className="mt-2.5 text-2xs leading-relaxed text-muted">
                  <strong className="text-ink">
                    {ZONE_BANDS.find((b) => b.key === aq.category?.key)?.plain
                      ?? 'Unknown'}
                  </strong>
                  {aq.trend_24h.change_pct != null && (
                    <> · {Math.abs(aq.trend_24h.change_pct).toFixed(0)}%{' '}
                      {aq.trend_24h.change_pct > 0 ? 'worse' : 'better'} than
                      this time yesterday</>
                  )}
                </p>
              </div>
            </div>

            {/* everything about right now */}
            <div className="grid content-start gap-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: 'City average', value: num(summary.data?.average_aqi, 0),
                    sub: `${summary.data?.reporting_stations ?? 0}/${summary.data?.station_count ?? 0} stations` },
                  { label: 'Main pollutant',
                    value: aq.dominant_pollutant
                      ? POLLUTANT_LABEL[aq.dominant_pollutant] ?? aq.dominant_pollutant
                      : '—',
                    sub: 'drives the index' },
                  { label: 'Wind', value: num(aq.weather?.wind_speed_mps, 1),
                    sub: 'm/s — disperses pollution' },
                  { label: 'Temperature', value: num(aq.weather?.temperature_c, 0),
                    sub: `°C · ${num(aq.weather?.humidity_pct, 0)}% humidity` },
                ].map((tile) => (
                  <div key={tile.label} className="card p-3.5">
                    <p className="label-eyebrow">{tile.label}</p>
                    <p className="mt-1 text-xl font-bold tnum text-ink">
                      {tile.value}
                    </p>
                    <p className="mt-0.5 text-2xs text-faint">{tile.sub}</p>
                  </div>
                ))}
              </div>

              {/* what to do — the citizen's real question */}
              {advisory.data?.available && (
                <div className="card card-pad border-brand/25 bg-brand-soft/40">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-bold text-ink">
                      What this means for you right now
                    </h3>
                    <span className="chip border-brand/30 bg-surface capitalize
                                     text-brand">
                      {advisory.data.risk_level} risk
                    </span>
                  </div>
                  <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {([['Going outside', advisory.data.outdoor_activity],
                       ['Exercise', advisory.data.exercise],
                       ['Mask', advisory.data.mask],
                       ['Windows', advisory.data.ventilation]] as const)
                      .map(([label, value]) => (
                        <div key={label}>
                          <dt className="text-2xs font-semibold uppercase
                                         tracking-wide text-brand">{label}</dt>
                          <dd className="mt-0.5 text-xs leading-relaxed text-muted">
                            {value}
                          </dd>
                        </div>
                      ))}
                  </dl>
                  <p className="mt-3 border-t border-brand/15 pt-2.5 text-2xs
                                text-faint">
                    {advisory.data.disclaimer}
                  </p>
                </div>
              )}

              {/* pollutant table */}
              {aq.pollutants.length > 0 && (
                <div className="card card-pad">
                  <h3 className="text-sm font-bold text-ink">
                    What is in the air
                  </h3>
                  <div className="mt-3 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-line text-2xs uppercase
                                       tracking-wide text-faint">
                          <th scope="col" className="py-1.5 pr-3 font-semibold">
                            Pollutant</th>
                          <th scope="col" className="py-1.5 pr-3 text-right
                                                     font-semibold">Amount</th>
                          <th scope="col" className="py-1.5 pr-3 text-right
                                                     font-semibold">As AQI</th>
                          <th scope="col" className="py-1.5 text-right font-semibold">
                            Share</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {aq.pollutants.map((p) => (
                          <tr key={p.key}>
                            <th scope="row" className="py-1.5 pr-3 font-semibold
                                                       text-ink">{p.label}</th>
                            <td className="py-1.5 pr-3 text-right tnum text-muted">
                              {num(p.concentration, 1)} {p.unit}</td>
                            <td className="py-1.5 pr-3 text-right">
                              <AqiPill aqi={p.sub_index} size="sm" /></td>
                            <td className="py-1.5 text-right tnum text-muted">
                              {p.share_of_aqi === null ? '—'
                                : `${num(p.share_of_aqi, 0)}%`}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

/* ── 2. history ─────────────────────────────────────────────────────── */

const RANGES = [
  { label: '24 hours', hours: 24 },
  { label: '7 days', hours: 168 },
  { label: '30 days', hours: 720 },
]
const METRICS: Array<{ key: keyof SeriesPoint; label: string; unit: string }> = [
  { key: 'aqi', label: 'AQI', unit: '' },
  { key: 'pm25', label: 'PM2.5', unit: 'µg/m³' },
  { key: 'pm10', label: 'PM10', unit: 'µg/m³' },
  { key: 'no2', label: 'NO₂', unit: 'ppb' },
]

function HistorySection() {
  const { citySlug } = useSelection()
  const [hours, setHours] = useState(168)
  const [metric, setMetric] = useState<keyof SeriesPoint>('aqi')

  const history = useQuery({ queryKey: ['history', citySlug, undefined, hours],
    queryFn: () => api.history({ city: citySlug, hours }),
    enabled: Boolean(citySlug) })
  const profile = useQuery({ queryKey: ['profile', citySlug, undefined],
    queryFn: () => api.hourlyProfile(citySlug), enabled: Boolean(citySlug) })
  const compare = useQuery({ queryKey: ['compare', citySlug, undefined, 'week'],
    queryFn: () => api.compare(citySlug, undefined, 'week'),
    enabled: Boolean(citySlug) })

  const active = METRICS.find((m) => m.key === metric)!

  return (
    <Section id="history" eyebrow="Step 2 — Understand" title="What the air has been doing"
             lede="Where today sits against the recent past, and the daily rhythm this
                   city repeats."
             tint>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-full border border-line bg-surface p-1">
          {RANGES.map((r) => (
            <button key={r.hours} type="button" onClick={() => setHours(r.hours)}
                    aria-pressed={hours === r.hours}
                    className={`rounded-full px-3.5 py-1.5 text-xs font-semibold
                                transition-colors ${
                      hours === r.hours ? 'bg-brand text-white'
                                        : 'text-muted hover:text-brand'}`}>
              {r.label}
            </button>
          ))}
        </div>
        <div className="inline-flex rounded-full border border-line bg-surface p-1">
          {METRICS.map((m) => (
            <button key={String(m.key)} type="button" onClick={() => setMetric(m.key)}
                    aria-pressed={metric === m.key}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold
                                transition-colors ${
                      metric === m.key ? 'bg-brand text-white'
                                       : 'text-muted hover:text-brand'}`}>
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {history.isLoading ? <ChartSkeleton height={260} /> : history.data ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ChartFrame title={`${active.label} over the last ${
              RANGES.find((r) => r.hours === hours)?.label}`}
                        provenance={history.data.provenance}>
              <TrendChart points={history.data.points} dataKey={metric}
                          label={active.label} unit={active.unit} height={260} />
            </ChartFrame>
          </div>
          <div className="grid content-start gap-4">
            <div className="card card-pad">
              <h3 className="text-sm font-bold text-ink">In this period</h3>
              <dl className="mt-3 space-y-2.5 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Average AQI</dt>
                  <dd><AqiPill aqi={history.data.stats.average_aqi} size="sm" /></dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Worst moment</dt>
                  <dd className="text-right">
                    <AqiPill aqi={history.data.stats.max_aqi} size="sm" />
                    <span className="mt-0.5 block text-2xs text-faint">
                      {fmtDateTime(history.data.stats.peak_at)}</span>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted">Cleanest moment</dt>
                  <dd className="text-right">
                    <AqiPill aqi={history.data.stats.min_aqi} size="sm" />
                    <span className="mt-0.5 block text-2xs text-faint">
                      {fmtDateTime(history.data.stats.cleanest_at)}</span>
                  </dd>
                </div>
              </dl>
              {compare.data?.change_pct != null && (
                <p className="mt-3 border-t border-line pt-3 text-xs text-muted">
                  This week is{' '}
                  <strong className={compare.data.change_pct > 0
                    ? 'text-accent' : 'text-good'}>
                    {Math.abs(compare.data.change_pct)}%{' '}
                    {compare.data.change_pct > 0 ? 'worse' : 'better'}
                  </strong>{' '}than last week.
                </p>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {profile.data && (
        <div className="mt-4">
          <ChartFrame title="The city's daily rhythm"
                      subtitle={`Average AQI by hour over ${profile.data.days} days, local time`}
                      footnote="Two peaks are the commute. The overnight rise is not new
                                pollution — it is the cooling air trapping what is
                                already there close to the ground.">
            <HourProfile byHour={profile.data.by_hour} height={200} />
          </ChartFrame>
        </div>
      )}
    </Section>
  )
}

/* ── 3. forecast ────────────────────────────────────────────────────── */

function ForecastSection() {
  const { citySlug } = useSelection()
  const [curveHours, setCurveHours] = useState(24)
  const prediction = useQuery({
    queryKey: ['prediction', citySlug, undefined, curveHours],
    queryFn: () => api.predictions(citySlug, undefined, curveHours),
    enabled: Boolean(citySlug) })

  return (
    <Section id="forecast" eyebrow="Step 3 — Predict" title="What happens next"
             lede="A machine-learning forecast from the city's own history, weather and
                   traffic rhythm — shown with the range the model is actually
                   confident about.">
      <div className="mb-4 inline-flex rounded-full border border-line bg-surface p-1">
        {[12, 24, 48, 72].map((h) => (
          <button key={h} type="button" onClick={() => setCurveHours(h)}
                  aria-pressed={curveHours === h}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-semibold
                              transition-colors ${
                    curveHours === h ? 'bg-brand text-white'
                                     : 'text-muted hover:text-brand'}`}>
            {h} h
          </button>
        ))}
      </div>

      {prediction.isLoading ? <ChartSkeleton height={300} />
        : prediction.isError ? <ErrorState error={prediction.error} />
        : prediction.data ? (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ChartFrame title={`AQI forecast — next ${curveHours} hours`}
                          provenance={prediction.data.provenance}
                          footnote="The shaded band is the model's 80% range: four times
                                    out of five the real value lands inside it.">
                <ForecastChart curve={prediction.data.curve}
                               currentAqi={prediction.data.current_aqi}
                               height={300} />
              </ChartFrame>
            </div>

            <div className="grid content-start gap-4">
              <div className="grid grid-cols-3 gap-2">
                {prediction.data.horizons.map((h) => (
                  <div key={h.horizon_hours} className="card p-3 text-center">
                    <p className="label-eyebrow">+{h.horizon_hours}h</p>
                    <p className="mt-1.5 text-xl font-bold tnum"
                       style={{ color: aqiColor(h.aqi) }}>{num(h.aqi, 0)}</p>
                    <p className="mt-0.5 text-2xs text-faint">
                      {num(h.aqi_lower, 0)}–{num(h.aqi_upper, 0)}
                    </p>
                  </div>
                ))}
              </div>

              {prediction.data.peak && (
                <div className="card card-pad">
                  <h3 className="text-sm font-bold text-ink">Worst window ahead</h3>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <p className="text-xs text-muted">
                      {fmtDateTime(prediction.data.peak.target_at)}
                    </p>
                    <AqiPill aqi={prediction.data.peak.aqi} />
                  </div>
                  {prediction.data.trough && (
                    <div className="mt-2.5 flex items-center justify-between gap-3
                                    border-t border-line pt-2.5">
                      <p className="text-xs text-muted">
                        Best window · {fmtDateTime(prediction.data.trough.target_at)}
                      </p>
                      <AqiPill aqi={prediction.data.trough.aqi} />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : null}
    </Section>
  )
}

/* ── 4. why ─────────────────────────────────────────────────────────── */

function WhySection() {
  const { citySlug } = useSelection()
  const sources = useQuery({ queryKey: ['sources', citySlug, undefined],
    queryFn: () => api.sources(citySlug), enabled: Boolean(citySlug) })
  const prediction = useQuery({ queryKey: ['prediction', citySlug, undefined, 24],
    queryFn: () => api.predictions(citySlug, undefined, 24),
    enabled: Boolean(citySlug) })
  const current = useQuery({ queryKey: ['current', citySlug, undefined],
    queryFn: () => api.current(citySlug), enabled: Boolean(citySlug) })

  return (
    <Section id="why" eyebrow="Step 4 — Explain" title="Why the air is like this"
             lede="AIRS reads the balance between pollutants, the weather and the
                   traffic to work out what is actually producing today's air — and
                   shows the evidence for each conclusion."
             tint>
      <div className="grid gap-4 lg:grid-cols-2">
        {sources.isLoading ? <CardSkeleton lines={7} /> : sources.data ? (
          <ChartFrame title="Where the pollution is coming from"
                      subtitle="Estimated share of today's pollutant load"
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
          <ChartFrame title="Which pollutant is driving the number"
                      subtitle="Compared on the AQI sub-index — the only scale on which µg/m³ and ppb can be compared"
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
    <Section id="solutions" eyebrow="Step 5 — Act" title="What can actually be done"
             lede="Two different questions, two different answers: what you can do
                   today, and what the city would have to do to move the number.">
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
                what-if simulator
              </Link>{' '}models what a real intervention would achieve here — applied
              only to the share of pollution that source is actually responsible for.
            </p>
          </div>
        </div>
      </div>
    </Section>
  )
}

/* ── 6. India map ───────────────────────────────────────────────────── */

function IndiaSection() {
  const { citySlug, setCity } = useSelection()
  const india = useQuery({ queryKey: ['india'], queryFn: () => api.india(),
    staleTime: 5 * 60 * 1000 })

  return (
    <Section id="india" eyebrow="The whole country"
             title="How every city compares"
             lede="Each circle is a city, coloured by the air-quality zone it is in
                   right now. Tap one to load it above."
             tint>
      {india.isLoading ? <ChartSkeleton height={480} />
        : india.isError ? <ErrorState error={india.error} />
        : india.data ? (
          <>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <div className="card px-4 py-2.5">
                <span className="label-eyebrow">National average</span>
                <span className="ml-2 text-lg font-bold tnum text-ink">
                  {num(india.data.national_average, 0)}
                </span>
              </div>
              <p className="text-xs text-muted">
                {india.data.reporting_cities} of {india.data.total_cities} cities
                reporting
              </p>
              <span className="ml-auto">
                <ProvenanceBadge provenance={india.data.provenance} />
              </span>
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
              <div>
                <IndiaMap cities={india.data.cities} selectedSlug={citySlug}
                          onSelect={setCity} height={520} />
                <div className="mt-3 card card-pad">
                  <ZoneLegend />
                </div>
              </div>

              <div className="grid content-start gap-4">
                <div className="card overflow-hidden">
                  <h3 className="border-b border-line px-4 py-2.5 text-sm font-bold
                                 text-ink">Worst air right now</h3>
                  <ul className="divide-y divide-line">
                    {india.data.worst.slice(0, 8).map((c, i) => (
                      <li key={c.slug}>
                        <button type="button" onClick={() => setCity(c.slug)}
                                className="flex w-full items-center gap-3 px-4 py-2
                                           text-left transition-colors
                                           hover:bg-raised">
                          <span className="w-4 text-2xs tnum text-faint">{i + 1}</span>
                          <span className="min-w-0 flex-1 truncate text-xs
                                           font-semibold text-ink">{c.name}</span>
                          <AqiPill aqi={c.aqi} size="sm" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="card overflow-hidden">
                  <h3 className="border-b border-line px-4 py-2.5 text-sm font-bold
                                 text-ink">Cleanest air right now</h3>
                  <ul className="divide-y divide-line">
                    {india.data.cleanest.slice(0, 6).map((c) => (
                      <li key={c.slug}>
                        <button type="button" onClick={() => setCity(c.slug)}
                                className="flex w-full items-center gap-3 px-4 py-2
                                           text-left transition-colors
                                           hover:bg-raised">
                          <span className="min-w-0 flex-1 truncate text-xs
                                           font-semibold text-ink">{c.name}</span>
                          <AqiPill aqi={c.aqi} size="sm" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </>
        ) : null}
    </Section>
  )
}

/* ── page ───────────────────────────────────────────────────────────── */

export default function Home() {
  return (
    <>
      <Hero />
      <HistorySection />
      <ForecastSection />
      <WhySection />
      <ActionSection />
      <IndiaSection />
    </>
  )
}
