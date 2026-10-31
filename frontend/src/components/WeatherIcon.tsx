/** Small colour weather glyphs keyed by WMO weather code. */
export function WeatherIcon({ code, isDay = true, size = 40 }:
  { code: number | null | undefined; isDay?: boolean; size?: number }) {
  const c = code ?? 0
  const kind = c === 0 || c === 1 ? (isDay ? 'sun' : 'moon')
    : c === 2 ? 'partly'
    : c === 3 ? 'cloud'
    : c === 45 || c === 48 ? 'fog'
    : c >= 95 ? 'storm'
    : (c >= 71 && c <= 77) || c === 85 || c === 86 ? 'snow'
    : 'rain'
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <defs>
        <linearGradient id="wi-sun" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#FDE047" /><stop offset="1" stopColor="#F59E0B" />
        </linearGradient>
        <linearGradient id="wi-cloud" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#F1F5F9" /><stop offset="1" stopColor="#CBD5E1" />
        </linearGradient>
      </defs>
      {(kind === 'sun' || kind === 'partly') && (
        <g>
          <circle cx={kind === 'sun' ? 24 : 18} cy={kind === 'sun' ? 24 : 18}
                  r={kind === 'sun' ? 10 : 8} fill="url(#wi-sun)" />
          {kind === 'sun' && [0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
            <line key={a} x1="24" y1="6" x2="24" y2="10" stroke="#F59E0B"
                  strokeWidth="3" strokeLinecap="round"
                  transform={`rotate(${a} 24 24)`} />
          ))}
        </g>
      )}
      {kind === 'moon' && (
        <path d="M30 10a14 14 0 1 0 8 25A12 12 0 0 1 30 10z" fill="#C7D2FE" />
      )}
      {kind !== 'sun' && kind !== 'moon' && (
        <path d="M14 36h20a8 8 0 0 0 0-16 11 11 0 0 0-21-2A8 8 0 0 0 14 36z"
              fill="url(#wi-cloud)" stroke="#94A3B8" strokeWidth="1" />
      )}
      {kind === 'rain' && [16, 24, 32].map((x) => (
        <line key={x} x1={x} y1="39" x2={x - 2} y2="45" stroke="#38BDF8"
              strokeWidth="2.6" strokeLinecap="round" />
      ))}
      {kind === 'storm' && (
        <path d="M24 36l-4 7h5l-3 5 8-9h-5l3-3z" fill="#FACC15" />
      )}
      {kind === 'snow' && [16, 24, 32].map((x) => (
        <circle key={x} cx={x} cy="42" r="2" fill="#E0F2FE" stroke="#7DD3FC" />
      ))}
      {kind === 'fog' && [38, 43].map((y) => (
        <line key={y} x1="10" y1={y} x2="38" y2={y} stroke="#94A3B8"
              strokeWidth="2.4" strokeLinecap="round" />
      ))}
    </svg>
  )
}
