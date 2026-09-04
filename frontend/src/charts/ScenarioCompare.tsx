import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer,
         Tooltip, XAxis, YAxis } from 'recharts'

import { TooltipShell } from './ChartFrame'
import { num } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'

/**
 * Baseline vs simulated, per pollutant, indexed to the baseline (100 = today).
 * Indexing is what makes PM10 at 120 µg/m³ and CO at 1 ppm comparable in one
 * frame — the alternative would be a dual axis, which is never acceptable.
 */
export function ScenarioCompare({ baseline, simulated, height = 250 }: {
  baseline: Record<string, number | null>
  simulated: Record<string, number | null>
  height?: number
}) {
  const viz = useVizTokens()
  const labels: Record<string, string> = {
    pm25: 'PM2.5', pm10: 'PM10', no2: 'NO₂', so2: 'SO₂', co: 'CO', o3: 'O₃' }

  const data = Object.keys(labels)
    .filter((k) => baseline[k] != null && simulated[k] != null && baseline[k] !== 0)
    .map((k) => ({
      key: k, label: labels[k],
      index: ((simulated[k] as number) / (baseline[k] as number)) * 100,
      before: baseline[k] as number,
      after: simulated[k] as number,
    }))

  if (!data.length) return null

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 18, right: 8, bottom: 4, left: -12 }}
                  barCategoryGap="30%">
          <CartesianGrid stroke={viz.grid} vertical={false} />
          <XAxis dataKey="label" stroke={viz.axis} tickLine={false}
                 axisLine={{ stroke: viz.grid }}
                 tick={{ fontSize: 12, fill: viz.axis }} />
          <YAxis domain={[0, 110]} stroke={viz.axis} tickLine={false}
                 axisLine={false} width={44} unit="%"
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <Tooltip cursor={{ fill: viz.grid, fillOpacity: 0.35 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as typeof data[number]
              return <TooltipShell title={d.label} rows={[
                { label: 'Now', value: num(d.before, 1) },
                { label: 'Simulated', value: num(d.after, 1), color: viz.series[2] },
                { label: 'Remaining', value: `${num(d.index, 1)}% of today` },
              ]} note="Modelled estimate, not a guaranteed outcome." />
            }} />
          <Bar dataKey="index" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.key}
                    fill={d.index < 97 ? viz.series[2] : viz.series[0]} />
            ))}
            <LabelList dataKey="index" position="top" offset={6}
                       formatter={(v: number) => `${v.toFixed(0)}%`}
                       style={{ fontSize: 11, fill: viz.ink, fontWeight: 600 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
