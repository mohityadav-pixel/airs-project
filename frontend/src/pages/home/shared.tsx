import type { ReactNode } from 'react'

export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
  'August', 'September', 'October', 'November', 'December']
export const MONTHS_SHORT = MONTHS.map((m) => m.slice(0, 3))

/** Section chrome shared by every block on the one-page dashboard. */
export function Section({ id, eyebrow, title, lede, children, tint = false, action }: {
  id: string; eyebrow: string; title: ReactNode; lede?: string
  children: ReactNode; tint?: boolean; action?: ReactNode
}) {
  return (
    <section id={id} className={tint ? 'bg-raised/50' : ''}>
      <div className="mx-auto max-w-content px-4 py-12 sm:px-6 sm:py-14">
        <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end
                           sm:justify-between">
          <div>
            <p className="text-2xs font-bold uppercase tracking-[0.2em] text-gradient">
              {eyebrow}
            </p>
            <h2 className="mt-1.5 text-xl font-extrabold tracking-tight text-ink
                           sm:text-2xl">{title}</h2>
            {lede && <p className="section-lede">{lede}</p>}
          </div>
          {action}
        </header>
        {children}
      </div>
    </section>
  )
}

export function Segmented<T extends string | number>({ options, value, onChange,
  label }: {
  options: Array<{ value: T; label: ReactNode }>; value: T
  onChange: (v: T) => void; label: string
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={String(o.value)} type="button" className="seg-btn"
                aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Big AQI number chip coloured by band. */
export function AqiBadge({ aqi, color, size = 'md' }:
  { aqi: number | null | undefined; color?: string | null; size?: 'sm' | 'md' | 'lg' }) {
  const dark = color === '#F4C542'
  const cls = size === 'lg' ? 'min-w-[3.5rem] px-3 py-1.5 text-lg'
    : size === 'sm' ? 'min-w-[2.25rem] px-2 py-0.5 text-2xs' : 'min-w-[2.75rem] px-2.5 py-1 text-xs'
  return (
    <span className={`inline-flex items-center justify-center rounded-lg font-extrabold
                      tnum ${cls}`}
          style={{ background: color ?? 'rgb(var(--c-line))',
                   color: dark ? '#1a1a19' : color ? '#fff' : 'rgb(var(--c-muted))' }}>
      {aqi ?? '—'}
    </span>
  )
}

const ICONS: Record<string, string> = {
  drop: 'M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z',
  wind: 'M3 8h11a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h8',
  sun: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  gauge: 'M12 14l4-4M3.5 17a9 9 0 1 1 17 0',
  run: 'M13 4a2 2 0 1 0 0 .1M9 20l3-6 3 3v4M6 12l3-3 4 1 3 3',
  mask: 'M3 9c3-1 5-2 9-2s6 1 9 2v3c0 4-4 7-9 7s-9-3-9-7zM7 12h10M8 15h8',
  window: 'M4 3h16v18H4zM12 3v18M4 12h16',
  heart: 'M12 20s-7-4.4-9-9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-2 4.6-9 9-9 9z',
  fan: 'M12 12a3 3 0 1 0 0 .1M12 9c0-4 1-6 3-6s3 3 0 6M15 12c4 0 6 1 6 3s-3 3-6 0M12 15c0 4-1 6-3 6s-3-3 0-6M9 12c-4 0-6-1-6-3s3-3 6 0',
  tree: 'M12 22v-6M7 16h10l-5-8zM8 11h8l-4-7z',
  pin: 'M12 21s7-5.3 7-11a7 7 0 1 0-14 0c0 5.7 7 11 7 11zM12 12.6a2.6 2.6 0 1 0 0-5.2 2.6 2.6 0 0 0 0 5.2z',
}

export function Icon({ name, size = 18, className = '' }:
  { name: keyof typeof ICONS | string; size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none"
         stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true" className={className}>
      <path d={ICONS[name] ?? ICONS.pin} />
    </svg>
  )
}
