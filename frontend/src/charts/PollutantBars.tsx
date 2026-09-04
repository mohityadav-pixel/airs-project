import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer,
         Tooltip, XAxis, YAxis } from 'recharts'

import { TooltipShell } from './ChartFrame'
import { aqiColor, categoryFor } from '@/lib/aqi'
import { num } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'
import type { Pollutant } from '@/lib/types'

/**
 * Pollutants compared on their AQI sub-index — the only axis on which they are
 * comparable at all, since µg/m³ and ppb are different quantities. Colour
 * encodes the AQI category (a status scale, not a series identity), and every
 * bar is directly labelled so the colour is never the only channel.
 */
export function PollutantBars({ pollutants, height = 260 }: {
  pollutants: Pollutant[]
  height?: number
}) {
  const viz = useVizTokens()
  const data = pollutants
    .filter((p) => p.sub_index !== null)
    .map((p) => ({
      key: p.key, label: p.label, sub: p.sub_index ?? 0,
      concentration: p.concentration, unit: p.unit,
      category: categoryFor(p.sub_index)?.label ?? '',
    }))

  if (!data.length) return null

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 18, right: 8, bottom: 4, left: -12 }}
                  barCategoryGap="28%">
          <CartesianGrid stroke={viz.grid} vertical={false} />
          <XAxis dataKey="label" stroke={viz.axis} tickLine={false}
                 axisLine={{ stroke: viz.grid }}
                 tick={{ fontSize: 12, fill: viz.axis }} />
          <YAxis stroke={viz.axis} tickLine={false} axisLine={false} width={44}
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <Tooltip cursor={{ fill: viz.grid, fillOpacity: 0.35 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as typeof data[number]
              return <TooltipShell title={d.label} rows={[
                { label: 'AQI sub-index', value: num(d.sub, 0),
                  color: aqiColor(d.sub) },
                { label: 'Concentration',
                  value: `${num(d.concentration, 1)} ${d.unit}` },
                { label: 'Band', value: d.category },
              ]} />
            }} />
          <Bar dataKey="sub" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.key} fill={aqiColor(d.sub)} />
            ))}
            <LabelList dataKey="sub" position="top" offset={6}
                       formatter={(v: number) => Math.round(v)}
                       style={{ fontSize: 11, fill: viz.ink, fontWeight: 600 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
