import { adviceFor } from '@/lib/advice'
import { num } from '@/lib/format'

import { useLive } from './LiveHero'
import { Icon, Section } from './shared'

const POLLUTANT_INFO: Record<string, { name: string; from: string; tone: string }> = {
  pm25: { name: 'Fine particles', from: 'Combustion, vehicles, burning', tone: '#6366F1' },
  pm10: { name: 'Coarse particles', from: 'Dust, construction, roads', tone: '#0EA5E9' },
  no2: { name: 'Nitrogen dioxide', from: 'Traffic exhaust, power plants', tone: '#F97316' },
  so2: { name: 'Sulphur dioxide', from: 'Coal, industry, refineries', tone: '#EAB308' },
  co: { name: 'Carbon monoxide', from: 'Incomplete combustion', tone: '#EC4899' },
  o3: { name: 'Ozone', from: 'Sunlight on NOx and VOCs', tone: '#14B8A6' },
}

export function PollutantsSection() {
  const live = useLive()
  const data = live.data
  if (!data) return null
  const advice = adviceFor(data.category?.key)

  return (
    <Section id="pollutants" eyebrow="Air Pollutants"
             title="Major Pollutants & Health Advisory"
             lede={data.source === 'measured'
               ? `Averaged over the ${data.pollutants[0]?.stations ?? 0} nearest monitoring stations. `
                 + 'Each pollutant is also shown on the AQI scale so they can be compared.'
               : data.source === 'calibrated'
                 ? 'No station has reported here in the last 3 hours. These are CAMS '
                   + 'model values, with particulates corrected to what nearby stations '
                   + 'have been measuring.'
                 : 'No monitoring station reports near this city, so these values come '
                   + 'from the CAMS atmospheric model.'}>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {data.pollutants.map((p) => {
          const info = POLLUTANT_INFO[p.key]
          const pct = Math.min(100, ((p.sub_index ?? 0) / 300) * 100)
          return (
            <div key={p.key} className="card relative overflow-hidden p-4">
              <span aria-hidden="true" className="absolute inset-x-0 top-0 h-1"
                    style={{ background: info?.tone }} />
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-extrabold text-ink">{p.label}</p>
                  <p className="text-2xs text-faint">{info?.name}</p>
                </div>
                {p.key === data.dominant_pollutant && (
                  <span className="rounded-full bg-accent-soft px-1.5 py-0.5 text-[9px]
                                   font-bold uppercase text-accent">Main</span>
                )}
              </div>
              <p className="mt-3 text-2xl font-black tnum text-ink">
                {num(p.concentration, p.key === 'co' ? 2 : 1)}
                <span className="ml-1 text-xs font-semibold text-faint">{p.unit}</span>
              </p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
                <div className="h-full rounded-full transition-all"
                     style={{ width: `${pct}%`, background: p.category?.color }} />
              </div>
              <p className="mt-1.5 flex items-center justify-between text-2xs">
                <span className="font-semibold" style={{ color: p.category?.color }}>
                  {p.category?.label ?? '—'}</span>
                <span className="tnum text-faint">AQI {p.sub_index ?? '—'}</span>
              </p>
              <p className="mt-2 text-[10px] leading-snug text-faint">{info?.from}</p>
            </div>
          )
        })}
      </div>

      {advice && (
        <div className="mt-6">
          <h3 className="mb-3 text-base font-extrabold text-ink">
            Health advice: <span style={{ color: data.category?.color }}>
              {advice.headline}</span>
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {([
              ['Going outside', advice.outdoor, 'tree', '#10B981'],
              ['Exercise', advice.exercise, 'run', '#0EA5E9'],
              ['Mask', advice.mask, 'mask', '#8B5CF6'],
              ['Windows', advice.windows, 'window', '#F59E0B'],
              ['Sensitive groups', advice.sensitive, 'heart', '#EC4899'],
              ['Air purifier', advice.purifier, 'fan', '#14B8A6'],
            ] as const).map(([label, text, icon, tone]) => (
              <div key={label} className="card flex gap-3 p-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center
                                 rounded-xl text-white"
                      style={{ background: tone }}>
                  <Icon name={icon} size={20} />
                </span>
                <div>
                  <p className="text-sm font-bold text-ink">{label}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted">{text}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-2xs text-faint">
            General public-health guidance, not medical advice. Follow your
            clinician’s advice for any existing condition.
          </p>
        </div>
      )}
    </Section>
  )
}
