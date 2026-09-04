import { aqiColor, categoryFor } from '@/lib/aqi'
import { num } from '@/lib/format'
import type { Trend } from '@/lib/types'

/**
 * The headline AQI figure. A hero number, not a chart: one value, so it gets
 * type and an arc rather than axes. The arc is a scale position cue, and the
 * category label carries the meaning so colour is never the only channel.
 */
export function AqiGauge({ aqi, trend, size = 200, label = 'Current AQI' }: {
  aqi: number | null
  trend?: Trend
  size?: number
  label?: string
}) {
  const category = categoryFor(aqi)
  const color = aqiColor(aqi)
  const fraction = aqi === null ? 0 : Math.min(aqi, 500) / 500

  const stroke = 12
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const arcSpan = 0.75                 // three-quarter dial
  const dash = circumference * arcSpan * fraction
  const gap = circumference - dash

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size * 0.8 }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}
             className="rotate-[135deg]" role="img"
             aria-label={aqi === null ? 'AQI unavailable'
               : `Air Quality Index ${Math.round(aqi)}, ${category?.label}`}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
                  stroke="rgb(var(--c-line))" strokeWidth={stroke}
                  strokeLinecap="round"
                  strokeDasharray={`${circumference * arcSpan} ${circumference}`} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
                  stroke={color} strokeWidth={stroke} strokeLinecap="round"
                  strokeDasharray={`${dash} ${gap}`}
                  style={{ transition: 'stroke-dasharray 600ms ease-out' }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center
                        pt-2 text-center">
          <span className="label-eyebrow">{label}</span>
          <span className="mt-0.5 text-5xl font-semibold leading-none text-ink">
            {aqi === null ? '—' : num(aqi, 0)}
          </span>
          {trend && trend.direction !== 'unknown' && (
            <span className="mt-1.5 text-xs text-muted">
              {trend.direction === 'worsening' ? '▲' :
               trend.direction === 'improving' ? '▼' : '▬'}{' '}
              {trend.change_pct === null ? trend.direction
                : `${Math.abs(trend.change_pct).toFixed(1)}% vs 1 h ago`}
            </span>
          )}
        </div>
      </div>
      {category && (
        <span className="mt-1 rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: `${color}22`, color }}>
          {category.label}
        </span>
      )}
    </div>
  )
}

/** Compact inline pill used in tables and lists. */
export function AqiPill({ aqi, size = 'md' }:
  { aqi: number | null; size?: 'sm' | 'md' }) {
  const color = aqiColor(aqi)
  const category = categoryFor(aqi)
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-lg font-semibold tnum
                      ${size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-sm'}`}
          style={{ backgroundColor: `${color}1f`, color }}
          title={category?.label}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }}
            aria-hidden="true" />
      {aqi === null ? '—' : Math.round(aqi)}
    </span>
  )
}
