import { AQI_CATEGORIES } from '@/lib/aqi'

const STOPS = [0, 50, 100, 150, 200, 300, 500]

/** The full US AQI scale with a pointer at the current value. */
export function AqiScale({ aqi, light = false }: { aqi: number | null; light?: boolean }) {
  const pos = aqi == null ? null : (() => {
    const v = Math.min(aqi, 500)
    const i = STOPS.findIndex((_s, k) => v <= STOPS[k + 1])
    const band = Math.max(0, i)
    const frac = (v - STOPS[band]) / (STOPS[band + 1] - STOPS[band])
    return ((band + frac) / 6) * 100
  })()
  return (
    <div className="w-full">
      <div className="flex justify-between text-[10px] font-semibold uppercase
                      tracking-wide" style={{ color: light ? 'rgba(255,255,255,.85)' : undefined }}>
        {AQI_CATEGORIES.map((c) => (
          <span key={c.key} className="w-1/6 truncate text-center">
            {c.key === 'usg' ? 'Sensitive' : c.label.replace('Very Unhealthy', 'V. Unhealthy')}
          </span>
        ))}
      </div>
      <div className="relative mt-1.5 h-2.5 rounded-full"
           style={{ background: `linear-gradient(90deg, ${AQI_CATEGORIES
             .map((c, i) => `${c.color} ${(i / 6) * 100}%, ${c.color} ${((i + 1) / 6) * 100}%`)
             .join(', ')})` }}>
        {pos !== null && (
          <span className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2
                           rounded-full border-[3px] border-white shadow-lg"
                style={{ left: `${pos}%`, background: 'rgba(15,23,42,.9)' }} />
        )}
      </div>
      <div className="mt-1 flex justify-between text-[10px] tnum"
           style={{ color: light ? 'rgba(255,255,255,.75)' : undefined }}>
        {STOPS.map((s) => <span key={s}>{s === 500 ? '500+' : s}</span>)}
      </div>
    </div>
  )
}
