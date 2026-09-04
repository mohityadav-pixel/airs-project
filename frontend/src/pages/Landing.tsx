import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { DataModeBanner } from '@/components/DataModeBanner'
import { Logo } from '@/components/Logo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AqiPill } from '@/components/AqiGauge'
import { api } from '@/lib/api'


const PILLARS = [
  {
    title: 'Observe',
    body: 'Live AQI and six pollutants across every monitoring station in the '
        + 'city, joined to weather and traffic on one hourly grid.',
  },
  {
    title: 'Understand',
    body: 'Estimated source attribution — traffic, industry, dust, burning or '
        + 'plain stagnation — with the evidence that produced each estimate.',
  },
  {
    title: 'Predict',
    body: 'A gradient-boosted forecast at 6, 24 and 72 hours with an 80% '
        + 'prediction interval, benchmarked against persistence.',
  },
  {
    title: 'Explain',
    body: 'Every forecast comes with a plain-language reason and a technical '
        + 'one. AIRS never shows a number it cannot account for.',
  },
  {
    title: 'Simulate',
    body: 'Ask what a 30% traffic cut would actually buy you — applied only to '
        + 'the share of pollution traffic is responsible for.',
  },
  {
    title: 'Act',
    body: 'Ranked interventions with a transparent priority score, so an '
        + 'official can argue with the ranking instead of trusting it blindly.',
  },
]

function CityTicker() {
  const { data } = useQuery({ queryKey: ['landing-cities'], queryFn: api.cities,
    staleTime: 600_000, retry: 0 })
  const summaries = useQuery({
    queryKey: ['landing-summaries', data?.map((c) => c.slug).join(',')],
    enabled: Boolean(data?.length),
    staleTime: 300_000,
    retry: 0,
    queryFn: async () => Promise.all(
      (data ?? []).slice(0, 4).map(async (city) => {
        try {
          const s = await api.summary(city.slug)
          return { name: city.name, aqi: s.average_aqi }
        } catch { return { name: city.name, aqi: null } }
      })),
  })

  if (!summaries.data?.length) return null
  return (
    <div className="mt-9 flex flex-wrap items-center gap-2.5">
      {summaries.data.map((row) => (
        <span key={row.name}
              className="inline-flex items-center gap-2 rounded-full border
                         border-line bg-surface px-3 py-1.5 text-xs text-muted">
          {row.name}
          <AqiPill aqi={row.aqi} size="sm" />
        </span>
      ))}
      <span className="text-2xs text-faint">city average AQI, live</span>
    </div>
  )
}

export default function Landing() {
  return (
    <div className="min-h-full bg-canvas">
      <DataModeBanner />
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link to="/login" className="btn-subtle px-3 py-1.5 text-xs">Sign in</Link>
        </div>
      </header>

      <section className="relative overflow-hidden">
        {/* Atmospheric gradient — one decorative element, not a theme. */}
        <div aria-hidden="true"
             className="pointer-events-none absolute inset-x-0 -top-40 h-[420px]
                        bg-[radial-gradient(60%_60%_at_50%_50%,rgb(var(--c-brand)/0.16),transparent_70%)]" />
        <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-10 sm:pt-16">
          <p className="label-eyebrow">AI Response &amp; Intervention System</p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-[1.08]
                         tracking-tight text-ink sm:text-6xl">
            From predicting pollution<br className="hidden sm:block" />
            {' '}to preventing it.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
            Most air-quality tools stop at the number on the dial. AIRS answers the
            four questions that follow it: why is pollution happening, what happens
            next, what can we do about it, and what would that actually achieve.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/dashboard" className="btn-primary px-5 py-3">
              Explore live air quality
            </Link>
            <Link to="/command-center" className="btn-ghost px-5 py-3">
              Open Command Center
            </Link>
          </div>

          <CityTicker />
        </div>
      </section>

      <section className="border-y border-line bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-14">
          <h2 className="text-2xs font-semibold uppercase tracking-widest text-faint">
            How AIRS works
          </h2>
          <p className="mt-3 max-w-2xl text-lg text-ink">
            Six stages, each feeding the next. Nothing in AIRS is a standalone
            widget.
          </p>
          <ol className="mt-9 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {PILLARS.map((pillar, i) => (
              <li key={pillar.title}>
                <span className="text-2xs font-semibold tnum text-brand">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="mt-1 text-base font-semibold text-ink">
                  {pillar.title}
                </h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">
                  {pillar.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-14">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:items-start">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-ink">
              Built so you can tell what kind of number you are looking at
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              A measurement, a forecast, a modelled scenario and a sentence written
              by a language model are four different things, and conflating them is
              how air-quality dashboards lose the trust of the people who have to
              act on them. In AIRS every value carries its provenance, in the API
              and on the screen. The Copilot is given a fixed block of AIRS data
              and is not permitted to produce a figure that is not in it.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {[
                ['Measured', 'text-good border-good/40 bg-good/10'],
                ['ML forecast', 'text-[#2a78d6] border-[#2a78d6]/40 bg-[#2a78d6]/10'],
                ['Modelled scenario', 'text-[#8B5CF6] border-[#8B5CF6]/40 bg-[#8B5CF6]/10'],
                ['Model estimate', 'text-usg border-usg/40 bg-usg/10'],
                ['AI explanation', 'text-[#e87ba4] border-[#e87ba4]/40 bg-[#e87ba4]/10'],
              ].map(([label, cls]) => (
                <span key={label}
                      className={`rounded-full border px-2.5 py-1 text-2xs
                                  font-semibold ${cls}`}>{label}</span>
              ))}
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border
                         border-line bg-line">
            {[
              ['6 / 24 / 72 h', 'Forecast horizons'],
              ['80%', 'Prediction interval on every point'],
              ['6', 'Source categories attributed'],
              ['6', 'Intervention levers you can simulate'],
              ['4', 'Roles, from citizen to administrator'],
              ['0', 'Numbers written by the language model'],
            ].map(([value, label]) => (
              <div key={label} className="bg-surface p-5">
                <dt className="text-xl font-semibold tracking-tight text-ink">
                  {value}
                </dt>
                <dd className="mt-1 text-xs text-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-2xs
                        text-faint sm:flex-row sm:items-center sm:justify-between">
          <Logo size={22} />
          <p className="max-w-xl sm:text-right">
            Forecasts, source attribution and simulations are model estimates, not
            guarantees. Health guidance is general public-health information and
            not medical advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
