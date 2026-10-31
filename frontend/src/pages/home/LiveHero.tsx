import { useQuery } from '@tanstack/react-query'

import { AirMascot } from '@/components/AirMascot'
import { AqiScale } from '@/components/AqiScale'
import { CitySearch } from '@/components/CitySearch'
import { ProvenanceBadge } from '@/components/Provenance'
import { CardSkeleton, ErrorState } from '@/components/State'
import { WeatherIcon } from '@/components/WeatherIcon'
import { adviceFor, bandStyle } from '@/lib/advice'
import { POLLUTANT_LABEL } from '@/lib/aqi'
import { num, relativeTime } from '@/lib/format'
import { insights } from '@/lib/insights'
import type { LiveCity } from '@/lib/insights'
import { useSelection } from '@/lib/selection'

import { Icon } from './shared'

export function useLive() {
  const { citySlug } = useSelection()
  return useQuery({ queryKey: ['insights-live', citySlug],
    queryFn: () => insights.live(citySlug!), enabled: Boolean(citySlug),
    refetchInterval: 5 * 60 * 1000 })
}

export function useIndia() {
  return useQuery({ queryKey: ['insights-india'], queryFn: insights.india,
    staleTime: 5 * 60 * 1000, refetchInterval: 10 * 60 * 1000 })
}

function ordinal(n: number) {
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

export function LiveHero() {
  const live = useLive()
  const india = useIndia()
  const { city } = useSelection()
  const data = live.data

  return (
    <section id="live" className="relative overflow-hidden">
      <div aria-hidden="true" className="aurora-bg pointer-events-none absolute inset-0" />
      <div className="relative mx-auto max-w-content px-4 pb-10 pt-6 sm:px-6 sm:pt-8">
        <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1.5
                                                text-xs font-semibold text-muted">
          <span>India</span>
          <span aria-hidden="true" className="text-faint">›</span>
          <span>{data?.city.state ?? '…'}</span>
          <span aria-hidden="true" className="text-faint">›</span>
          <span className="text-brand">{data?.city.name ?? city?.name ?? '…'}</span>
        </nav>

        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end
                        sm:justify-between">
          <div>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider ${
              data?.provenance?.mode === 'demo'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : data?.provenance?.kind === 'estimated'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                : data?.provenance?.kind === 'observed'
                ? 'pill-live bg-emerald-600/90 text-white'
                : 'bg-raised text-faint'
            }`}>
              {data?.provenance?.mode === 'demo' ? 'DEMO DATA' :
               data?.provenance?.kind === 'estimated' ? 'MODEL ESTIMATE' :
               data?.provenance?.kind === 'observed' ? 'LIVE' : 'CHECKING'}
            </span>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-ink
                           sm:text-4xl">
              {data?.city.name ?? city?.name ?? 'India'}{' '}
              <span className="text-gradient">Air Quality Index</span>
            </h1>
            <p className="mt-1 text-sm text-muted">
              AI-powered air quality monitoring and forecasting for {data?.city.name ?? city?.name ?? 'selected region'}
              {data && <> · updated {relativeTime(data.observed_at)}</>}
            </p>
          </div>
          <CitySearch />
        </div>

        {live.isError && (
          <div className="mt-6"><ErrorState error={live.error}
                                            onRetry={() => live.refetch()} /></div>
        )}
        {live.isLoading && (
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2"><CardSkeleton lines={7} /></div>
            <CardSkeleton lines={7} />
          </div>
        )}

        {data && (
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <AqiCard data={data} rank={india.data?.cities.find(
              (c) => c.slug === data.city.slug)?.rank}
                     total={india.data?.reporting_cities} />
            <WeatherCard data={data} />
          </div>
        )}
      </div>
    </section>
  )
}

function AqiCard({ data, rank, total }: { data: LiveCity; rank?: number; total?: number }) {
  const band = bandStyle(data.category?.key)
  const advice = adviceFor(data.category?.key)
  const pm25 = data.pollutants.find((p) => p.key === 'pm25')
  const pm10 = data.pollutants.find((p) => p.key === 'pm10')
  const change = data.yesterday.change_pct

  return (
    <div className="relative overflow-hidden rounded-3xl p-5 shadow-lift sm:p-7
                    lg:col-span-2"
         style={{ background: `linear-gradient(135deg, ${band.from}, ${band.to})`,
                  color: band.text }}>
      <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-16
                                          h-64 w-64 rounded-full bg-white/15 blur-2xl" />
      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center
                      sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold opacity-90">Live AQI</span>
            <span className="rounded-full bg-black/20 px-2 py-0.5 text-2xs font-semibold">
              {data.provenance?.mode === 'demo'
                ? 'Demo Synthetic'
                : data.source === 'measured'
                ? 'Station Measured'
                : data.source === 'calibrated'
                ? 'Calibrated Model'
                : 'Modelled Estimate'}
            </span>
          </div>
          <div className="mt-1 flex items-end gap-3">
            <span className="text-7xl font-black leading-none tracking-tighter tnum
                             sm:text-8xl">{data.aqi ?? '—'}</span>
            <span className="mb-2 text-sm font-semibold opacity-80">AQI (US)</span>
          </div>
          <div className="mt-3 inline-flex rounded-xl glass px-3.5 py-1.5 text-lg
                          font-extrabold">
            {data.category?.label ?? 'No data'}
          </div>
          {advice && <p className="mt-2 text-sm font-medium opacity-90">
            {advice.headline}</p>}
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm font-semibold">
            <span>PM2.5 <strong className="text-lg tnum">{num(pm25?.concentration, 0)}</strong>
              <span className="text-xs opacity-80"> µg/m³</span></span>
            <span>PM10 <strong className="text-lg tnum">{num(pm10?.concentration, 0)}</strong>
              <span className="text-xs opacity-80"> µg/m³</span></span>
          </div>
        </div>
        <div className="self-center sm:self-auto">
          <AirMascot band={data.category?.key} size={170} />
        </div>
      </div>

      <div className="relative mt-6"><AqiScale aqi={data.aqi} light /></div>

      <div className="relative mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ['Main pollutant', data.dominant_pollutant
            ? POLLUTANT_LABEL[data.dominant_pollutant] ?? data.dominant_pollutant : '—'],
          ['24 h range', data.range_24h.min != null
            ? `${data.range_24h.min}–${data.range_24h.max}` : '—'],
          ['vs yesterday', change == null ? '—'
            : `${change > 0 ? '▲' : change < 0 ? '▼' : '■'} ${Math.abs(change).toFixed(0)}%`],
          ['National rank', rank && total ? `${ordinal(rank)} of ${total}` : '—'],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl glass px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider opacity-80">
              {label}</p>
            <p className="mt-0.5 text-base font-extrabold tnum">{value}</p>
          </div>
        ))}
      </div>
      <div className="relative mt-4 flex flex-wrap items-center justify-between gap-2
                      text-2xs font-medium opacity-90">
        <span>{data.source_label}</span>
        <span className="rounded-full bg-white/90 px-1 py-0.5 text-ink">
          <ProvenanceBadge provenance={data.provenance} showSource={false} />
        </span>
      </div>
    </div>
  )
}

function WeatherCard({ data }: { data: LiveCity }) {
  const w = data.weather
  if (!w) {
    return <div className="card card-pad text-sm text-muted">Weather unavailable.</div>
  }
  const windKmh = w.wind_speed_mps != null ? w.wind_speed_mps * 3.6 : null
  const dir = w.wind_deg != null ? COMPASS[Math.round(w.wind_deg / 45) % 8] : ''
  return (
    <div className="card relative overflow-hidden p-5 sm:p-6">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0
            bg-gradient-to-br from-sky-400/15 via-indigo-400/10 to-fuchsia-400/15" />
      <div className="relative">
        <p className="label-eyebrow">Weather now</p>
        <div className="mt-2 flex items-center gap-3">
          <WeatherIcon code={w.code} isDay={w.is_day} size={64} />
          <div>
            <p className="text-4xl font-black tnum text-ink">
              {num(w.temperature_c, 0)}<span className="text-xl align-top">°C</span>
            </p>
            <p className="text-sm font-semibold text-muted">{w.condition ?? '—'}</p>
          </div>
        </div>
        <p className="mt-1 text-xs text-faint">Feels like {num(w.feels_like_c, 0)}°C</p>
        <dl className="mt-4 grid grid-cols-2 gap-2">
          {[
            ['Humidity', `${num(w.humidity_pct, 0)} %`, 'drop', 'text-sky-500'],
            ['Wind', `${num(windKmh, 1)} km/h ${dir}`, 'wind', 'text-teal-500'],
            ['UV index', num(w.uv_index, 1), 'sun', 'text-amber-500'],
            ['Pressure', `${num(w.pressure_hpa, 0)} hPa`, 'gauge', 'text-indigo-500'],
          ].map(([label, value, icon, tone]) => (
            <div key={label} className="rounded-xl bg-raised/80 px-3 py-2">
              <dt className="flex items-center gap-1 text-2xs font-semibold text-faint">
                <Icon name={icon} size={13} className={tone} /> {label}</dt>
              <dd className="mt-0.5 text-sm font-bold tnum text-ink">{value}</dd>
            </div>
          ))}
        </dl>
        {w.daily.length > 1 && (
          <ul className="mt-4 space-y-1.5 border-t border-line pt-3">
            {w.daily.slice(1, 4).map((d) => (
              <li key={d.date} className="flex items-center gap-2 text-xs">
                <span className="w-14 font-semibold text-muted">
                  {new Date(`${d.date}T12:00:00+05:30`).toLocaleDateString('en-IN',
                    { weekday: 'short', timeZone: 'Asia/Kolkata' })}</span>
                <WeatherIcon code={d.code} size={24} />
                <span className="min-w-0 flex-1 truncate text-faint">{d.condition}</span>
                <span className="tnum font-semibold text-ink">
                  {Math.round(d.t_min)}° / {Math.round(d.t_max)}°</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-2xs leading-relaxed text-faint">
          Low wind lets pollution pile up; rain and a breeze clear it out.
        </p>
      </div>
    </div>
  )
}
