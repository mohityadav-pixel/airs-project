import type { ReactNode } from 'react'

import { ProvenanceBadge } from '@/components/Provenance'
import type { Provenance } from '@/lib/types'

/**
 * Every chart in AIRS sits in this frame: title, optional subtitle, the
 * provenance badge, the legend row, then the plot. Keeping the anatomy in one
 * component is what makes twelve charts read as one system.
 */
export function ChartFrame({ title, subtitle, provenance, legend, actions,
                             footnote, children }: {
  title: string
  subtitle?: string
  provenance?: Provenance
  legend?: ReactNode
  actions?: ReactNode
  footnote?: ReactNode
  children: ReactNode
}) {
  return (
    <figure className="card card-pad">
      <figcaption className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          {provenance && <ProvenanceBadge provenance={provenance} />}
        </div>
      </figcaption>
      {legend && <div className="mb-3">{legend}</div>}
      {children}
      {footnote && (
        <p className="mt-3 border-t border-line pt-2.5 text-2xs text-faint">
          {footnote}
        </p>
      )}
    </figure>
  )
}

export function Legend({ items }: {
  items: Array<{ color: string; label: string; shape?: 'line' | 'dot' | 'band' }>
}) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-1.5 text-xs
                                        text-muted">
          {item.shape === 'band' ? (
            <span className="h-3 w-3.5 rounded-sm" aria-hidden="true"
                  style={{ backgroundColor: item.color, opacity: 0.28 }} />
          ) : item.shape === 'line' ? (
            <span className="h-0.5 w-4 rounded-full" aria-hidden="true"
                  style={{ backgroundColor: item.color }} />
          ) : (
            <span className="h-2.5 w-2.5 rounded-full" aria-hidden="true"
                  style={{ backgroundColor: item.color }} />
          )}
          {item.label}
        </li>
      ))}
    </ul>
  )
}

export function TooltipShell({ title, rows, note }: {
  title: string
  rows: Array<{ label: string; value: string; color?: string }>
  note?: string
}) {
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 shadow-lift">
      <p className="text-2xs font-medium text-faint">{title}</p>
      <ul className="mt-1.5 space-y-1">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-4
                                         text-xs">
            <span className="inline-flex items-center gap-1.5 text-muted">
              {row.color && (
                <span className="h-2 w-2 rounded-full" aria-hidden="true"
                      style={{ backgroundColor: row.color }} />
              )}
              {row.label}
            </span>
            <span className="font-medium tnum text-ink">{row.value}</span>
          </li>
        ))}
      </ul>
      {note && <p className="mt-1.5 text-2xs text-faint">{note}</p>}
    </div>
  )
}
