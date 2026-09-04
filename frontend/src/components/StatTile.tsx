import type { ReactNode } from 'react'

/** A stat tile is the right form when the data's job is a single headline —
 *  no axes, no plot, just the figure with its unit and change. */
export function StatTile({ label, value, unit, delta, deltaTone = 'neutral',
                           footnote, icon }: {
  label: string
  value: ReactNode
  unit?: string
  delta?: string
  deltaTone?: 'good' | 'bad' | 'neutral'
  footnote?: string
  icon?: ReactNode
}) {
  const toneClass = deltaTone === 'good' ? 'text-good'
    : deltaTone === 'bad' ? 'text-unhealthy' : 'text-muted'
  return (
    <div className="card card-pad">
      <div className="flex items-start justify-between gap-2">
        <span className="label-eyebrow">{label}</span>
        {icon}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold text-ink">{value}</span>
        {unit && <span className="text-xs text-faint">{unit}</span>}
      </div>
      {delta && <p className={`mt-1 text-xs font-medium ${toneClass}`}>{delta}</p>}
      {footnote && <p className="mt-1.5 text-2xs text-faint">{footnote}</p>}
    </div>
  )
}
