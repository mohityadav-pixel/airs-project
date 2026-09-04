/** AQI presentation helpers. The scale itself is defined by the EPA and is
 *  identical in light and dark mode — these colours are data, not decoration. */

export const AQI_CATEGORIES = [
  { key: 'good', label: 'Good', lower: 0, upper: 50, color: '#00A86B' },
  { key: 'moderate', label: 'Moderate', lower: 51, upper: 100, color: '#F4C542' },
  { key: 'usg', label: 'Unhealthy for Sensitive Groups', lower: 101, upper: 150, color: '#F08A24' },
  { key: 'unhealthy', label: 'Unhealthy', lower: 151, upper: 200, color: '#E14B4B' },
  { key: 'very_unhealthy', label: 'Very Unhealthy', lower: 201, upper: 300, color: '#8B5CF6' },
  { key: 'hazardous', label: 'Hazardous', lower: 301, upper: 500, color: '#7E1F2B' },
] as const

export function categoryFor(aqi: number | null | undefined) {
  if (aqi === null || aqi === undefined) return null
  return AQI_CATEGORIES.find((c) => aqi <= c.upper) ?? AQI_CATEGORIES[AQI_CATEGORIES.length - 1]
}

export function aqiColor(aqi: number | null | undefined, fallback = '#94A8BB') {
  return categoryFor(aqi)?.color ?? fallback
}

/** White text is unreadable on the yellow band; everything else needs it. */
export function onColor(hex: string) {
  return hex === '#F4C542' ? '#1a1a19' : '#ffffff'
}

export const POLLUTANT_LABEL: Record<string, string> = {
  pm25: 'PM2.5', pm10: 'PM10', no2: 'NO₂', so2: 'SO₂', co: 'CO', o3: 'O₃',
}

export const SEVERITY_STYLE: Record<string, { dot: string; label: string }> = {
  info: { dot: '#2a78d6', label: 'Info' },
  watch: { dot: '#eda100', label: 'Watch' },
  warning: { dot: '#eb6834', label: 'Warning' },
  emergency: { dot: '#d03b3b', label: 'Emergency' },
}

export const ZONE_LABEL: Record<string, string> = {
  residential: 'Residential', commercial: 'Commercial', industrial: 'Industrial',
  traffic_corridor: 'Traffic corridor', construction: 'Construction',
  green: 'Green space', mixed: 'Mixed use',
}
