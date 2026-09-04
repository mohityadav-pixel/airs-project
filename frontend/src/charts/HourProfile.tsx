import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis,
         YAxis } from 'recharts'

import { TooltipShell } from './ChartFrame'
import { aqiColor } from '@/lib/aqi'
import { num } from '@/lib/format'
import { useVizTokens } from '@/lib/viz'

/** Average AQI by local hour — the shape that tells an official when to act. */
export function HourProfile({ byHour, height = 220 }: {
  byHour: Array<{ hour: number; average_aqi: number | null; samples: number }>
  height?: number
}) {
  const viz = useVizTokens()
  const data = byHour.map((d) => ({
    ...d,
    value: d.average_aqi ?? 0,
    label: `${String(d.hour).padStart(2, '0')}:00`,
  }))

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -12 }}
                  barCategoryGap="18%">
          <CartesianGrid stroke={viz.grid} vertical={false} />
          <XAxis dataKey="hour" stroke={viz.axis} tickLine={false}
                 axisLine={{ stroke: viz.grid }} interval={2}
                 tickFormatter={(h: number) => `${h}h`}
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <YAxis stroke={viz.axis} tickLine={false} axisLine={false} width={40}
                 tick={{ fontSize: 11, fill: viz.axis }} />
          <Tooltip cursor={{ fill: viz.grid, fillOpacity: 0.35 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as typeof data[number]
              return <TooltipShell title={`${d.label} local`} rows={[
                { label: 'Average AQI', value: num(d.value, 0),
                  color: aqiColor(d.value) },
                { label: 'Samples', value: String(d.samples) },
              ]} />
            }} />
          <Bar dataKey="value" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {data.map((d) => <Cell key={d.hour} fill={aqiColor(d.value)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
