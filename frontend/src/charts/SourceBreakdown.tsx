import { SOURCE_SLOT, useVizTokens } from '@/lib/viz'
import { num } from '@/lib/format'
import type { SourceContribution } from '@/lib/types'

/**
 * Source shares. A labelled proportion bar rather than a pie: the reader's job
 * is to compare six parts and read each value, which a pie does badly. Every
 * row carries its own value label, which is also the relief for the three
 * light-mode palette slots that sit below 3:1 contrast on white.
 *
 * Colour is bound to the source category by fixed slot, so re-sorting the list
 * never repaints a source.
 */
export function SourceBreakdown({ contributions, confidence }: {
  contributions: SourceContribution[]
  confidence?: number
}) {
  const viz = useVizTokens()
  const colorFor = (key: string) =>
    viz.series[SOURCE_SLOT[key] ?? viz.series.length - 1] ?? viz.series[0]

  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-line"
           role="img"
           aria-label={contributions.map((c) =>
             `${c.label} ${c.share_pct}%`).join(', ')}>
        {contributions.map((c) => (
          <span key={c.key}
                title={`${c.label} — ${c.share_pct}%`}
                style={{ width: `${c.share_pct}%`, backgroundColor: colorFor(c.key),
                         // 2px surface gap keeps adjacent fills separable.
                         boxShadow: `inset -2px 0 0 rgb(var(--c-surface))` }} />
        ))}
      </div>

      <ul className="mt-3.5 space-y-2">
        {contributions.map((c) => (
          <li key={c.key} className="flex items-center gap-2.5">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" aria-hidden="true"
                  style={{ backgroundColor: colorFor(c.key) }} />
            <span className="min-w-0 flex-1 truncate text-xs text-muted">
              {c.label}
            </span>
            <span className="w-24 shrink-0">
              <span className="block h-1.5 rounded-full bg-line">
                <span className="block h-1.5 rounded-full"
                      style={{ width: `${Math.min(c.share_pct * 2, 100)}%`,
                               backgroundColor: colorFor(c.key) }} />
              </span>
            </span>
            <span className="w-11 shrink-0 text-right text-xs font-semibold tnum
                             text-ink">
              {num(c.share_pct, 0)}%
            </span>
          </li>
        ))}
      </ul>

      {confidence !== undefined && (
        <p className="mt-3 border-t border-line pt-2.5 text-2xs text-faint">
          Attribution confidence {Math.round(confidence * 100)}%. These are
          model-based estimates from pollutant ratios, meteorology and site
          context — not a chemical speciation measurement.
        </p>
      )}
    </div>
  )
}
