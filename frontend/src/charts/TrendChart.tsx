import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis,
         YAxis } from 'recharts'

import { TooltipShell } from './ChartFrame'
import { fmtDateTime, num } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'
import type { SeriesPoint } from '@/lib/types'

/** History of one measure over time. One series, so no legend — the title
 *  names it. */
export function TrendChart({ points, dataKey = 'aqi', label = 'AQI',
                             unit = '', height = 240 }: {
  points: SeriesPoint[]
  dataKey?: keyof SeriesPoint
  label?: string
  unit?: string
  height?: number
}) {
  const viz = useVizTokens()
  const data = points.map((p) => ({ at: p.at, value: p[dataKey] as number | null }))

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -10 }}>
          <defs>
            <linearGradient id={`fill-${String(dataKey)}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={viz.series[0]} stopOpacity={0.28} />
              <stop offset="100%" stopColor={viz.series[0]} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={viz.grid} vertical={false} />
          <XAxis dataKey="at" stroke={viz.axis} tickLine={false}
                 axisLine={{ stroke: viz.grid }} minTickGap={40}
                 tick={{ fontSize: 11, fill: viz.axis }}
                 tickFormatter={(v) => new Date(v).toLocaleString('en-IN',
                   { day: 'numeric', month: 'short', hour: 'numeric', hour12: true,
                     timeZone: 'Asia/Kolkata' })} />
          <YAxis stroke={viz.axis} tickLine={false} axisLine={false} width={44}
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <Tooltip
            cursor={{ stroke: viz.axis, strokeWidth: 1, strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as typeof data[number]
              return <TooltipShell title={fmtDateTime(d.at)} rows={[
                { label, value: `${num(d.value, unit ? 1 : 0)}${unit ? ` ${unit}` : ''}`,
                  color: viz.series[0] }]} />
            }} />
          <Area type="monotone" dataKey="value" stroke={viz.series[0]}
                strokeWidth={2} fill={`url(#fill-${String(dataKey)})`}
                dot={false} connectNulls
                activeDot={{ r: 4, strokeWidth: 2, stroke: viz.surface }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
