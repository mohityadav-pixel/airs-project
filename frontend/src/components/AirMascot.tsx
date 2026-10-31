/**
 * AIRS's own mascot: a round puff of air whose face follows the AQI band.
 * Original artwork, drawn in SVG.
 */
export function AirMascot({ band, size = 140 }: { band?: string | null; size?: number }) {
  const b = band ?? 'moderate'
  const mood: Record<string, { mouth: string; brow?: string; cheek: string
                                body: string; haze: number }> = {
    good: { mouth: 'M40 70 Q60 88 80 70', cheek: '#FDA4AF', body: '#ECFEFF', haze: 0 },
    moderate: { mouth: 'M44 74 Q60 82 76 74', cheek: '#FDBA74', body: '#FEFCE8', haze: 0.1 },
    usg: { mouth: 'M46 78 L74 78', cheek: '#FDBA74', body: '#FFF7ED', haze: 0.25,
           brow: 'M36 44 L50 48 M70 48 L84 44' },
    unhealthy: { mouth: 'M44 82 Q60 70 76 82', cheek: '#FCA5A5', body: '#FFF1F2', haze: 0.4,
                 brow: 'M36 46 L50 42 M70 42 L84 46' },
    very_unhealthy: { mouth: 'M46 84 Q60 68 74 84', cheek: '#C4B5FD', body: '#F5F3FF', haze: 0.55,
                      brow: 'M36 46 L50 40 M70 40 L84 46' },
    hazardous: { mouth: 'M46 84 Q60 66 74 84', cheek: '#FDA4AF', body: '#FFE4E6', haze: 0.7,
                 brow: 'M36 46 L50 38 M70 38 L84 46' },
  }
  const m = mood[b] ?? mood.moderate
  const masked = b === 'unhealthy' || b === 'very_unhealthy' || b === 'hazardous'
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden="true">
      <defs>
        <radialGradient id="mascot-body" cx="0.4" cy="0.35" r="0.75">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor={m.body} />
        </radialGradient>
      </defs>
      <g className="origin-center animate-[bob_4s_ease-in-out_infinite]">
        <path d="M24 78c-12 0-18-9-16-18 2-8 9-12 16-11 1-15 13-27 30-27
                 13 0 23 7 27 18 3-1 6-2 9-2 14 0 24 11 22 24-2 10-10 16-20 16z"
              fill="url(#mascot-body)" stroke="rgba(15,23,42,.18)" strokeWidth="2" />
        <circle cx="46" cy="56" r="5" fill="#0F172A" />
        <circle cx="74" cy="56" r="5" fill="#0F172A" />
        <circle cx="47.5" cy="54.5" r="1.6" fill="#fff" />
        <circle cx="75.5" cy="54.5" r="1.6" fill="#fff" />
        {m.brow && <path d={m.brow} stroke="#0F172A" strokeWidth="3"
                         strokeLinecap="round" fill="none" />}
        <ellipse cx="36" cy="66" rx="6" ry="3.5" fill={m.cheek} opacity=".8" />
        <ellipse cx="84" cy="66" rx="6" ry="3.5" fill={m.cheek} opacity=".8" />
        {masked ? (
          <g>
            <path d="M40 66h40v12c0 6-9 10-20 10s-20-4-20-10z" fill="#E0F2FE"
                  stroke="#7DD3FC" strokeWidth="2" />
            <path d="M40 68L30 62M80 68l10-6" stroke="#7DD3FC" strokeWidth="2" />
            <path d="M46 74h28M46 79h28" stroke="#BAE6FD" strokeWidth="1.6" />
          </g>
        ) : (
          <path d={m.mouth} stroke="#0F172A" strokeWidth="3.4" strokeLinecap="round"
                fill="none" />
        )}
      </g>
      {m.haze > 0 && [0, 1, 2, 3, 4, 5].map((i) => (
        <circle key={i} cx={14 + i * 18} cy={100 + (i % 2) * 8} r={3 + (i % 3)}
                fill="#64748B" opacity={m.haze * 0.8} />
      ))}
    </svg>
  )
}
