const IST = 'Asia/Kolkata'

export function fmtTime(iso?: string | null, opts: Intl.DateTimeFormatOptions = {}) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: IST, ...opts })
}

export function fmtDateTime(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    hour12: true, timeZone: IST })
}

export function fmtDate(iso?: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: IST })
}

export function relativeTime(iso?: string | null) {
  if (!iso) return 'unknown'
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  return `${Math.round(hours / 24)} d ago`
}

export function num(value: number | null | undefined, digits = 0, fallback = '—') {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback
  return value.toLocaleString('en-IN', {
    minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function signed(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return '—'
  const formatted = num(Math.abs(value), digits)
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${formatted}`
}

export function compactNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return Intl.NumberFormat('en-IN', { notation: 'compact',
    maximumFractionDigits: 1 }).format(value)
}

export function titleCase(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
