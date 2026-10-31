export function Logo({ size = 30, withWordmark = true }:
  { size?: number; withWordmark?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none"
           aria-hidden="true" className="shrink-0">
        <rect width="32" height="32" rx="8" className="fill-brand" />
        <path d="M5 12h13a3 3 0 1 0-3-3" stroke="white" strokeWidth="2.1"
              strokeLinecap="round" />
        <path d="M5 17h17a3.2 3.2 0 1 1-3.2 3.2" stroke="white" strokeWidth="2.1"
              strokeLinecap="round" opacity=".8" />
        <path d="M5 22h7" stroke="white" strokeWidth="2.1" strokeLinecap="round"
              opacity=".55" />
      </svg>
      {withWordmark && (
        <span className="flex flex-col leading-none">
          <span className="text-base font-semibold tracking-tight text-ink">AIRS</span>
          <span className="mt-0.5 text-[9px] uppercase tracking-[0.18em] text-faint">
            Air Quality Intelligence
          </span>
        </span>
      )}
    </span>
  )
}
