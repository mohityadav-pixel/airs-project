/**
 * The provenance badge is the visual half of the AIRS promise that a reader can
 * always tell measurement from forecast from simulation from AI prose. Every
 * data panel carries one.
 */
import { useState } from 'react'

import { relativeTime } from '@/lib/format'
import type { DataKind, Provenance as ProvenanceType } from '@/lib/types'

const KIND_META: Record<DataKind, { label: string; tone: string; note: string }> = {
  observed: {
    label: 'Measured', tone: 'text-good border-good/35 bg-good/10',
    note: 'Recorded by a monitoring station.',
  },
  predicted: {
    label: 'ML forecast', tone: 'text-[#2a78d6] border-[#2a78d6]/35 bg-[#2a78d6]/10',
    note: 'Produced by the AIRS forecasting model. Not a measurement.',
  },
  simulated: {
    label: 'Modelled scenario',
    tone: 'text-[#8B5CF6] border-[#8B5CF6]/35 bg-[#8B5CF6]/10',
    note: 'A what-if estimate, not a prediction of what will happen.',
  },
  estimated: {
    label: 'Model estimate', tone: 'text-usg border-usg/35 bg-usg/10',
    note: 'Inferred by AIRS from measured data. Uncertain by nature.',
  },
  ai_generated: {
    label: 'AI explanation',
    tone: 'text-[#e87ba4] border-[#e87ba4]/35 bg-[#e87ba4]/10',
    note: 'Written by a language model from AIRS data. Figures come from AIRS, '
        + 'not from the model.',
  },
}

export function ProvenanceBadge({ provenance, showSource = true }:
  { provenance: ProvenanceType; showSource?: boolean }) {
  const [open, setOpen] = useState(false)
  const meta = KIND_META[provenance.kind]
  const stamp = provenance.observed_at ?? provenance.generated_at

  return (
    <div className="relative inline-flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setOpen(false)}
        aria-expanded={open}
        className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5
                    text-2xs font-semibold ${meta.tone}`}
      >
        {meta.label}
        {provenance.mode === 'demo' && (
          <span className="rounded-sm bg-current/15 px-1 py-px text-[9px] uppercase
                           tracking-wider">demo</span>
        )}
        {provenance.mode === 'cached' && (
          <span className="rounded-sm bg-current/15 px-1 py-px text-[9px] uppercase
                           tracking-wider">cached</span>
        )}
      </button>
      {showSource && stamp && (
        <span className="text-2xs text-faint">{relativeTime(stamp)}</span>
      )}
      {open && (
        <div className="absolute left-0 top-full z-30 mt-1.5 w-72 rounded-xl border
                        border-line bg-surface p-3 text-xs shadow-lift">
          <p className="font-medium text-ink">{meta.label}</p>
          <p className="mt-1 text-muted">{meta.note}</p>
          <dl className="mt-2.5 space-y-1 border-t border-line pt-2.5 text-2xs">
            <div className="flex justify-between gap-3">
              <dt className="text-faint">Source</dt>
              <dd className="text-right text-muted">{provenance.source}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-faint">Mode</dt>
              <dd className="text-muted">{provenance.mode}</dd>
            </div>
            {stamp && (
              <div className="flex justify-between gap-3">
                <dt className="text-faint">Timestamp</dt>
                <dd className="text-muted">{new Date(stamp).toLocaleString('en-IN',
                  { timeZone: 'Asia/Kolkata' })}</dd>
              </div>
            )}
          </dl>
          {provenance.note && (
            <p className="mt-2 border-t border-line pt-2 text-2xs text-faint">
              {provenance.note}
            </p>
          )}
          {provenance.is_stale && (
            <p className="mt-2 text-2xs font-medium text-usg">
              This reading is older than expected — the upstream feed may be delayed.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
