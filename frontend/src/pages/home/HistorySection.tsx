import { useMemo, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip,
         XAxis, YAxis } from 'recharts'

import { ProvenanceBadge } from '@/components/Provenance'
import { ChartSkeleton, ErrorState } from '@/components/State'
import { aqiColor, categoryFor } from '@/lib/aqi'
import { num } from '@/lib/format'
import { insights } from '@/lib/insights'
import type { History } from '@/lib/insights'
import { useSelection } from '@/lib/selection'

import { MONTHS, MONTHS_SHORT, Section, Segmented } from './shared'

const METRICS = [
  { value: 'aqi', label: 'AQI' }, { value: 'pm25', label: 'PM2.5' },
  { value: 'pm10', label: 'PM10' }, { value: 'co', label: 'CO' },
  { value: 'so2', label: 'SO₂' }, { value: 'no2', label: 'NO₂' },
  { value: 'o3', label: 'O₃' },
]
const YEAR_COLORS = ['#60A5FA', '#A78BFA', '#34D399', '#F472B6', '#FB923C', '#22D3EE']

function yearColor(years: number[], y: number, current: number) {
  if (y === current) return '#F59E0B'
  return YEAR_COLORS[years.filter((x) => x !== current).indexOf(y) % YEAR_COLORS.length]
}

export function HistorySection() {
  const { citySlug } = useSelection()
  const now = new Date()
  const currentYear = Number(now.toLocaleString('en-IN', { year: 'numeric',
                                                         timeZone: 'Asia/Kolkata' }))
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [metric, setMetric] = useState('aqi')
  const [hidden, setHidden] = useState<number[]>([])

  const history = useQuery({ queryKey: ['insights-history', citySlug, month, metric],
    queryFn: () => insights.history(citySlug!, month, metric),
    enabled: Boolean(citySlug), staleTime: 30 * 60 * 1000,
    placeholderData: keepPreviousData })
  const h = history.data

  return (
    <Section id="history" eyebrow="Historical Analysis"
             title={<>{MONTHS[month - 1]} Air Quality, Year on Year</>}
             lede="Daily averages for the same month in every year since 2022, so you
                   can see whether this year is better or worse than usual.">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Segmented label="Pollutant" value={metric} onChange={setMetric} options={METRICS} />
        <label className="ml-auto flex items-center gap-2 text-xs font-semibold text-muted">
          Month
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}
                  className="input w-auto py-1.5 pr-8 text-xs font-semibold">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </label>
      </div>

      {history.isError && <ErrorState error={history.error}
                                      onRetry={() => history.refetch()} />}
      {history.isLoading && <ChartSkeleton height={380} />}
      {h && (
        <>
          <div className={`card card-pad transition-opacity ${
            history.isFetching ? 'opacity-60' : ''}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-extrabold text-ink">
                  {MONTHS[h.month - 1]} {h.metric_label} analysis
                </h3>
                <p className="text-sm font-semibold text-brand">
                  {h.city.name}{h.city.state ? `, ${h.city.state}` : ''}, India
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {h.years.map((y) => {
                  const off = hidden.includes(y)
                  return (
                    <button key={y} type="button"
                            onClick={() => setHidden((v) => off ? v.filter((x) => x !== y)
                                                                : [...v, y])}
                            className={`inline-flex items-center gap-1.5 rounded-full border
                                        border-line px-2.5 py-1 text-xs font-semibold
                                        transition-opacity ${off ? 'opacity-40' : ''}`}>
                      <span className="h-2.5 w-2.5 rounded-full"
                            style={{ background: yearColor(h.years, y, currentYear) }} />
                      {y}
                    </button>
                  )
                })}
              </div>
            </div>
            <YearChart h={h} hidden={hidden} currentYear={currentYear} />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-2xs text-faint">
                {h.calibration.applied
                  ? `Model values scaled ×${h.calibration.factor} to match ${h.calibration.days} days of station data.`
                  : 'Daily means of the CAMS atmospheric model. Dots on the current year mark its AQI band.'}
              </p>
              <ProvenanceBadge provenance={h.provenance} showSource={false} />
            </div>
          </div>

          <Summary h={h} currentYear={currentYear} />
          <MonthlyGrid h={h} />
          {metric === 'aqi' && h.calendar.length > 0 && (
            <Calendar h={h} year={currentYear} />
          )}
        </>
      )}
    </Section>
  )
}

function YearChart({ h, hidden, currentYear }:
  { h: History; hidden: number[]; currentYear: number }) {
  const rows = useMemo(() => {
    const n = Math.max(...h.series.map((s) => s.days.length), 0)
    return Array.from({ length: n }, (_, i) => {
      const row: Record<string, number | null> = { day: i + 1 }
      for (const s of h.series) {
        row[`y${s.year}`] = s.days[i]?.value ?? null
        if (s.days[i]?.measured != null) row[`m${s.year}`] = s.days[i].measured ?? null
      }
      return row
    })
  }, [h])
  const isAqi = h.metric === 'aqi'
  const cur = h.series.find((s) => s.year === currentYear)
  const curAvg = cur ? cur.days.filter((d) => d.value != null)
    .reduce((a, d, _, arr) => a + (d.value ?? 0) / arr.length, 0) : null
  const fill = isAqi ? aqiColor(curAvg) : '#F59E0B'

  return (
    <div className="mt-4" style={{ height: 360 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 10, right: 8, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="cur-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor={fill} stopOpacity={0.55} />
              <stop offset="1" stopColor={fill} stopOpacity={0.08} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="rgb(var(--viz-grid))" />
          <XAxis dataKey="day" tickFormatter={(d) => `${MONTHS_SHORT[h.month - 1]} ${d}`}
                 interval={2} tick={{ fontSize: 10, fill: 'rgb(var(--viz-axis))' }}
                 axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: 'rgb(var(--viz-axis))' }} axisLine={false}
                 tickLine={false} width={48}
                 label={{ value: h.unit || h.metric_label, angle: -90, position: 'insideLeft',
                          offset: 18, fontSize: 10, fill: 'rgb(var(--viz-axis))' }} />
          <Tooltip content={<YearTooltip h={h} currentYear={currentYear} />}
                   cursor={{ stroke: 'rgb(var(--viz-axis))', strokeDasharray: '4 4' }} />
          {h.series.filter((s) => s.year !== currentYear && !hidden.includes(s.year))
            .map((s) => (
              <Line key={s.year} type="monotone" dataKey={`y${s.year}`}
                    stroke={yearColor(h.years, s.year, currentYear)} strokeWidth={1.8}
                    strokeOpacity={0.85} dot={false} connectNulls isAnimationActive={false} />
            ))}
          {cur && !hidden.includes(currentYear) && (
            <Area type="monotone" dataKey={`y${currentYear}`} stroke={fill}
                  strokeWidth={2.6} fill="url(#cur-fill)" connectNulls={false}
                  isAnimationActive={false}
                  dot={(props: { cx?: number; cy?: number; index?: number
                                 payload?: Record<string, number | null> }) => {
                    const v = props.payload?.[`y${currentYear}`]
                    return v == null || props.cx == null || props.cy == null
                      ? <g key={props.index} /> : (
                      <circle key={props.index} cx={props.cx} cy={props.cy} r={3.6}
                              fill={isAqi ? aqiColor(v) : fill}
                              stroke="rgb(var(--c-surface))" strokeWidth={1.2} />)
                  }} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function YearTooltip({ active, payload, label, h, currentYear }: {
  active?: boolean; label?: number; h: History; currentYear: number
  payload?: Array<{ payload: Record<string, number | null> }> }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  const years = [...h.years].sort((a, b) => b - a)
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2.5 text-xs shadow-lift">
      <p className="mb-1.5 font-bold text-ink">{MONTHS_SHORT[h.month - 1]}. {label}</p>
      {years.map((y) => {
        const v = row[`y${y}`]
        return (
          <p key={y} className="flex items-center gap-2 py-0.5">
            <span className="h-2.5 w-2.5 rounded-full"
                  style={{ background: yearColor(h.years, y, currentYear) }} />
            <span className="font-semibold text-muted">{y}:</span>
            <span className="font-bold tnum"
                  style={{ color: h.metric === 'aqi' ? aqiColor(v) : undefined }}>
              {v == null ? '—' : num(v, h.metric === 'aqi' ? 0 : 1)}
            </span>
            {row[`m${y}`] != null && <span className="text-2xs text-faint">
              (stations {row[`m${y}`]})</span>}
          </p>
        )
      })}
    </div>
  )
}

function Summary({ h, currentYear }: { h: History; currentYear: number }) {
  const s = h.summary.this_year
  const change = h.summary.change_vs_last_year_pct
  const isAqi = h.metric === 'aqi'
  const fmt = (v: number | null | undefined) => num(v, isAqi ? 0 : 1)
  const tiles = [
    { label: `${MONTHS_SHORT[h.month - 1]} ${currentYear} average`,
      value: fmt(s?.avg), color: isAqi ? aqiColor(s?.avg) : undefined,
      sub: isAqi ? categoryFor(s?.avg)?.label : h.unit },
    { label: 'Cleanest day', value: fmt(s?.best),
      color: isAqi ? aqiColor(s?.best) : undefined,
      sub: s ? `${MONTHS_SHORT[h.month - 1]} ${s.best_day}` : '—' },
    { label: 'Most polluted day', value: fmt(s?.worst),
      color: isAqi ? aqiColor(s?.worst) : undefined,
      sub: s ? `${MONTHS_SHORT[h.month - 1]} ${s.worst_day}` : '—' },
    { label: `vs ${currentYear - 1}`, value: change == null ? '—'
        : `${change > 0 ? '+' : ''}${change.toFixed(0)}%`,
      color: change == null ? undefined : change > 0 ? '#E14B4B' : '#00A86B',
      sub: change == null ? 'no comparison yet' : change > 0 ? 'worse than last year'
        : 'better than last year' },
  ]
  if (!s) return null
  return (
    <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="card p-4">
          <p className="label-eyebrow">{t.label}</p>
          <p className="mt-1 text-3xl font-black tnum" style={{ color: t.color }}>{t.value}</p>
          <p className="text-2xs font-semibold text-faint">{t.sub}</p>
        </div>
      ))}
    </div>
  )
}

function MonthlyGrid({ h }: { h: History }) {
  const isAqi = h.metric === 'aqi'
  const max = Math.max(1, ...h.monthly.flatMap((r) => r.months.map((v) => v ?? 0)))
  const cellColor = (v: number | null) => {
    if (v == null) return undefined
    if (isAqi) return aqiColor(v)
    const t = v / max
    return `rgb(${Math.round(56 + t * 180)} ${Math.round(189 - t * 120)} ${Math.round(248 - t * 90)})`
  }
  return (
    <div className="card card-pad mt-4 overflow-x-auto">
      <h3 className="text-sm font-bold text-ink">Monthly averages</h3>
      <p className="text-2xs text-faint">Every month since the archive began — the seasonal
        pattern at a glance.</p>
      <table className="mt-3 w-full min-w-[640px] border-separate border-spacing-1 text-center
                        text-2xs">
        <thead>
          <tr>
            <th className="w-12 text-left font-semibold text-faint">Year</th>
            {MONTHS_SHORT.map((m) => (
              <th key={m} className="font-semibold text-faint">{m}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {h.monthly.map((r) => (
            <tr key={r.year}>
              <th className="text-left text-xs font-bold text-ink">{r.year}</th>
              {r.months.map((v, i) => {
                const bg = cellColor(v)
                return (
                  <td key={i} className="rounded-md py-2 font-bold tnum"
                      style={{ background: bg ?? 'rgb(var(--c-raised))',
                               color: bg ? (bg === '#F4C542' ? '#1a1a19' : '#fff')
                                         : 'rgb(var(--c-faint))' }}>
                    {v == null ? '·' : num(v, isAqi ? 0 : 0)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Calendar({ h, year }: { h: History; year: number }) {
  const byDate = new Map(h.calendar.map((d) => [d.date, d]))
  const start = new Date(Date.UTC(year, 0, 1))
  const offset = start.getUTCDay()
  const cells: Array<{ date: string; aqi: number | null } | null> = []
  for (let i = 0; i < offset; i++) cells.push(null)
  const days = (Date.UTC(year + 1, 0, 1) - start.getTime()) / 86400000
  for (let i = 0; i < days; i++) {
    const d = new Date(start.getTime() + i * 86400000).toISOString().slice(0, 10)
    cells.push({ date: d, aqi: byDate.get(d)?.aqi ?? null })
  }
  const counts: Record<string, number> = {}
  h.calendar.forEach((d) => {
    const k = categoryFor(d.aqi)?.label
    if (k) counts[k] = (counts[k] ?? 0) + 1
  })
  return (
    <div className="card card-pad mt-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-ink">{year} at a glance</h3>
          <p className="text-2xs text-faint">One square per day, coloured by its average AQI.</p>
        </div>
        <div className="flex flex-wrap gap-2 text-2xs">
          {Object.entries(counts).map(([k, v]) => (
            <span key={k} className="chip">{k}: <strong className="tnum text-ink">{v}</strong> days</span>
          ))}
        </div>
      </div>
      <div className="mt-3 overflow-x-auto pb-1">
        <div className="grid grid-flow-col grid-rows-7 gap-[3px]" style={{ width: 'max-content' }}>
          {cells.map((c, i) => (
            <span key={i} title={c ? `${c.date}: AQI ${c.aqi ?? '—'}` : undefined}
                  className="h-3 w-3 rounded-[3px]"
                  style={{ background: c == null ? 'transparent'
                    : c.aqi == null ? 'rgb(var(--c-line) / .6)' : aqiColor(c.aqi) }} />
          ))}
        </div>
      </div>
    </div>
  )
}
