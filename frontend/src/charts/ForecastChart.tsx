import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer,
         Tooltip, XAxis, YAxis } from 'recharts'

import { Legend, TooltipShell } from './ChartFrame'
import { AQI_CATEGORIES } from '@/lib/aqi'
import { fmtTime, num } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'
import type { ForecastPoint } from '@/lib/types'

/**
 * AQI forecast: one measure over time, so a line — with the 80% interval as a
 * band behind it rather than as a second axis or a second chart. The observed
 * "now" value is marked so the reader can see where measurement ends and
 * forecast begins; that boundary is the whole point of the chart.
 */
export function ForecastChart({ curve, currentAqi, height = 280 }: {
  curve: ForecastPoint[]
  currentAqi: number | null
  height?: number
}) {
  const viz = useVizTokens()
  if (!curve.length) return null

  const data = curve.map((p) => ({
    at: p.target_at,
    hour: p.horizon_hours,
    aqi: p.aqi,
    band: p.aqi_lower !== null && p.aqi_upper !== null
      ? [p.aqi_lower, p.aqi_upper] : undefined,
    lower: p.aqi_lower,
    upper: p.aqi_upper,
  }))

  const values = data.flatMap((d) => [d.upper, d.lower, d.aqi])
    .filter((v): v is number => v !== null && v !== undefined)
    .concat(currentAqi !== null ? [currentAqi] : [])
  const maxValue = Math.max(...values, 10)
  const minValue = Math.min(...values, maxValue)
  const ceiling = Math.ceil((maxValue * 1.12) / 25) * 25
  // A line over time reads by shape, so the axis is padded around the data
  // rather than pinned to zero — but a series that genuinely sits near zero
  // keeps the true baseline, so "low" still looks low.
  const floorValue = minValue < 25 ? 0 : Math.floor((minValue * 0.82) / 25) * 25

  // Category bands as recessive background rules — orientation, not decoration.
  const guides = AQI_CATEGORIES.filter(
    (c) => c.upper < ceiling && c.upper > floorValue)

  return (
    <>
      <Legend items={[
        { color: viz.series[0], label: 'Forecast AQI', shape: 'line' },
        { color: viz.band, label: '80% prediction interval', shape: 'band' },
      ]} />
      <div style={{ height }} className="mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
            <CartesianGrid stroke={viz.grid} strokeDasharray="0" vertical={false} />
            {guides.map((g) => (
              <ReferenceLine key={g.key} y={g.upper} stroke={g.color}
                             strokeOpacity={0.35} strokeDasharray="3 4"
                             label={{ value: g.label.replace('Unhealthy for Sensitive Groups', 'USG'),
                                      position: 'insideTopLeft', fontSize: 9,
                                      fill: viz.axis }} />
            ))}
            <XAxis dataKey="at" tickFormatter={(v) => fmtTime(v)}
                   stroke={viz.axis} tick={{ fontSize: 11, fill: viz.axis }}
                   tickLine={false} axisLine={{ stroke: viz.grid }} minTickGap={28} />
            <YAxis domain={[floorValue, ceiling]} stroke={viz.axis}
                   tick={{ fontSize: 11, fill: viz.axis }} tickLine={false}
                   axisLine={false} width={44} />
            <Tooltip
              cursor={{ stroke: viz.axis, strokeWidth: 1, strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0].payload as typeof data[number]
                return (
                  <TooltipShell
                    title={`In ${d.hour} h · ${fmtTime(d.at)}`}
                    rows={[
                      { label: 'Forecast AQI', value: num(d.aqi, 0),
                        color: viz.series[0] },
                      { label: '80% interval',
                        value: `${num(d.lower, 0)} – ${num(d.upper, 0)}` },
                    ]}
                    note="ML forecast, not a measurement." />
                )
              }} />
            <Area type="monotone" dataKey="band" stroke="none" fill={viz.band}
                  fillOpacity={0.22} isAnimationActive={false} connectNulls />
            <Line type="monotone" dataKey="aqi" stroke={viz.series[0]}
                  strokeWidth={2} dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: viz.surface }} />
            {currentAqi !== null && (
              <ReferenceLine y={currentAqi} stroke={viz.series[1]} strokeWidth={1.5}
                             strokeDasharray="5 4"
                             label={{ value: `now ${Math.round(currentAqi)}`,
                                      position: 'insideBottomLeft', fontSize: 10,
                                      offset: 6, fill: viz.series[1] }} />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
