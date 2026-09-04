import { Bar, BarChart, Cell, LabelList, ReferenceLine, ResponsiveContainer,
         Tooltip, XAxis, YAxis } from 'recharts'

import { TooltipShell } from './ChartFrame'
import { titleCase } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'

/**
 * Correlation is a signed quantity around a meaningful zero, so it gets a
 * diverging encoding: two poles with a neutral centre, and a zero rule.
 */
export function CorrelationBars({ rows, height = 260 }: {
  rows: Array<{ driver: string; vs_aqi: number | null; interpretation: string }>
  height?: number
}) {
  const viz = useVizTokens()
  const data = rows
    .filter((r) => r.vs_aqi !== null)
    .map((r) => ({ driver: titleCase(r.driver.replace(/_(mps|c|pct|hpa|index)$/, '')),
                   value: r.vs_aqi as number, note: r.interpretation }))
    .sort((a, b) => b.value - a.value)

  if (!data.length) return null

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical"
                  margin={{ top: 4, right: 40, bottom: 4, left: 10 }}
                  barCategoryGap="26%">
          <XAxis type="number" domain={[-1, 1]} stroke={viz.axis} tickLine={false}
                 axisLine={false} tick={{ fontSize: 11, fill: viz.axis }} />
          <YAxis type="category" dataKey="driver" width={116} stroke={viz.axis}
                 tickLine={false} axisLine={false}
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <ReferenceLine x={0} stroke={viz.axis} strokeWidth={1} />
          <Tooltip cursor={{ fill: viz.grid, fillOpacity: 0.3 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as typeof data[number]
              return <TooltipShell title={d.driver}
                rows={[{ label: 'r (vs AQI)', value: d.value.toFixed(2) }]}
                note={d.note} />
            }} />
          <Bar dataKey="value" radius={3} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.driver}
                    fill={d.value >= 0 ? viz.series[1] : viz.series[0]} />
            ))}
            <LabelList dataKey="value" position="right" offset={6}
                       formatter={(v: number) => v.toFixed(2)}
                       style={{ fontSize: 11, fill: viz.ink, fontWeight: 600 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
