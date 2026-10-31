import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis,
         YAxis } from 'recharts'

import { ProvenanceBadge } from '@/components/Provenance'
import { ChartSkeleton, ErrorState } from '@/components/State'
import { WeatherIcon } from '@/components/WeatherIcon'
import { aqiColor, categoryFor } from '@/lib/aqi'
import { insights } from '@/lib/insights'
import { useSelection } from '@/lib/selection'

import { useLive } from './LiveHero'
import { AqiBadge, Section, Segmented } from './shared'

function hourLabel(at: string) {
  const h = Number(at.slice(11, 13))
  const suffix = h < 12 ? 'am' : 'pm'
  return `${h % 12 === 0 ? 12 : h % 12}${suffix}`
}

function dayLabel(iso: string, i: number) {
  if (i === 0) return 'Today'
  const d = new Date(`${iso}T12:00:00+05:30`)
  return d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric',
                                          timeZone: 'Asia/Kolkata' })
}

function AqiTooltip({ active, payload }: { active?: boolean
  payload?: Array<{ payload: { at: string; aqi: number | null; kind?: string } }> }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const cat = categoryFor(p.aqi)
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-lift">
      <p className="font-semibold text-ink">
        {new Date(`${p.at}:00+05:30`).toLocaleString('en-IN', {
          weekday: 'short', hour: 'numeric', timeZone: 'Asia/Kolkata' })}
      </p>
      <p className="mt-0.5"><strong style={{ color: cat?.color }}>AQI {p.aqi ?? '—'}</strong>
        <span className="ml-1 text-faint">{cat?.label}</span></p>
      {p.kind && <p className="text-2xs text-faint">
        {p.kind === 'observed' ? 'Measured' : p.kind === 'predicted' ? 'Atmospheric model forecast' : 'Model estimate'}</p>}
    </div>
  )
}

export function ForecastSection() {
  const { citySlug } = useSelection()
  const live = useLive()
  const [view, setView] = useState<'past' | 'next'>('next')
  const forecast = useQuery({ queryKey: ['insights-forecast', citySlug],
    queryFn: () => insights.forecast(citySlug!), enabled: Boolean(citySlug) })

  const past = (live.data?.past_24h ?? []).map((p) => ({ ...p }))
  if (live.data) {
    past.push({ at: live.data.generated_at.slice(0, 13) + ':00', hours_ago: 0,
                aqi: live.data.aqi, kind: 'observed' as const })
  }
  const next = (forecast.data?.hours ?? []).slice(0, 48)
  const chartData = view === 'past' ? past : next

  return (
    <Section id="forecast" eyebrow="Air Quality Forecast" title="48-Hour Forecast & 5-Day Outlook"
             lede={live.data?.source === 'measured'
               ? "The Copernicus (CAMS) atmospheric model, calibrated to today's station readings. Plan outdoor time around the green and yellow hours."
               : "Atmospheric model estimates for the hours ahead. Plan outdoor time around the green and yellow hours."}
             tint
             action={<Segmented label="Chart view" value={view} onChange={setView}
                                options={[{ value: 'past', label: 'Past 24 h' },
                                          { value: 'next', label: 'Next 48 h' }]} />}>
      {forecast.isError && <ErrorState error={forecast.error} />}
      <div className="card card-pad">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-ink">
            {view === 'past' ? 'Hourly AQI, last 24 hours' : 'Hourly AQI forecast, next 48 hours'}
          </h3>
          {forecast.data && <ProvenanceBadge provenance={view === 'past'
            ? (live.data?.provenance ?? forecast.data.provenance) : forecast.data.provenance} />}
        </div>
        {chartData.length === 0 ? <ChartSkeleton height={240} /> : (
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="rgb(var(--viz-grid))" />
                <XAxis dataKey="at" tickFormatter={hourLabel} interval={view === 'past' ? 2 : 5}
                       tick={{ fontSize: 10, fill: 'rgb(var(--viz-axis))' }}
                       axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'rgb(var(--viz-axis))' }}
                       axisLine={false} tickLine={false} width={44} />
                <Tooltip content={<AqiTooltip />} cursor={{ fill: 'rgb(var(--c-line) / .35)' }} />
                <Bar dataKey="aqi" radius={[5, 5, 0, 0]} maxBarSize={18}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={aqiColor(d.aqi)}
                          fillOpacity={'kind' in d && d.kind === 'estimated' ? 0.75 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {forecast.isLoading ? <div className="mt-4"><ChartSkeleton height={150} /></div>
        : forecast.data && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {forecast.data.days.slice(0, 5).map((d, i) => (
            <div key={d.date} className="card relative overflow-hidden p-4 text-center">
              <span aria-hidden="true" className="absolute inset-x-0 top-0 h-1.5"
                    style={{ background: d.category?.color }} />
              <p className="text-sm font-bold text-ink">{dayLabel(d.date, i)}</p>
              <div className="mt-1 flex justify-center">
                <WeatherIcon code={d.weather?.code} size={44} />
              </div>
              <p className="text-2xs text-faint">{d.weather?.condition ?? ''}</p>
              <div className="mt-2 flex items-center justify-center gap-2">
                <AqiBadge aqi={d.avg} color={d.category?.color} />
              </div>
              <p className="mt-1 text-2xs font-semibold"
                 style={{ color: d.category?.color }}>{d.category?.label}</p>
              <p className="mt-1 text-2xs tnum text-faint">AQI {d.min}–{d.max}</p>
              {d.weather && (
                <p className="mt-1 text-2xs tnum text-muted">
                  {Math.round(d.weather.t_min)}° / {Math.round(d.weather.t_max)}°C
                  {d.weather.rain_chance != null && ` · ${d.weather.rain_chance}% rain`}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {forecast.data?.best_window && forecast.data.peak && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="card flex items-center justify-between gap-3 p-4">
            <div>
              <p className="label-eyebrow text-good">Cleanest hour ahead</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {new Date(`${forecast.data.best_window.at}:00+05:30`).toLocaleString(
                  'en-IN', { weekday: 'long', hour: 'numeric', timeZone: 'Asia/Kolkata' })}
              </p>
            </div>
            <AqiBadge aqi={forecast.data.best_window.aqi}
                      color={forecast.data.best_window.category?.color} size="lg" />
          </div>
          <div className="card flex items-center justify-between gap-3 p-4">
            <div>
              <p className="label-eyebrow text-accent">Worst hour ahead</p>
              <p className="mt-1 text-sm font-semibold text-ink">
                {new Date(`${forecast.data.peak.at}:00+05:30`).toLocaleString(
                  'en-IN', { weekday: 'long', hour: 'numeric', timeZone: 'Asia/Kolkata' })}
              </p>
            </div>
            <AqiBadge aqi={forecast.data.peak.aqi}
                      color={forecast.data.peak.category?.color} size="lg" />
          </div>
        </div>
      )}
    </Section>
  )
}
