import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { insights } from '@/lib/insights'
import { useSelection } from '@/lib/selection'

/**
 * City picker for a 270-city network. A plain <select> with 70 options is
 * unusable on a phone, so this is a search box with a keyboard-navigable list
 * and the metros offered as one-tap chips.
 */
const QUICK = ['delhi', 'mumbai', 'bengaluru', 'kolkata', 'chennai', 'hyderabad']

export function CitySearch({ compact = false }: { compact?: boolean }) {
  const { cities, citySlug, city, setCity } = useSelection()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const boxRef = useRef<HTMLDivElement>(null)
  const meta = useQuery({ queryKey: ['insights-cities'], queryFn: insights.cities,
    staleTime: 60 * 60 * 1000 })
  const stateOf = useMemo(() => new Map((meta.data ?? []).map((c) => [c.slug, c.state])),
    [meta.data])

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return cities.slice(0, 10)
    return cities
      .filter((c) => c.name.toLowerCase().includes(needle)
                  || c.slug.includes(needle)
                  || (stateOf.get(c.slug) ?? '').toLowerCase().includes(needle))
      .sort((a, b) => {
        const ap = a.name.toLowerCase().startsWith(needle) ? 0 : 1
        const bp = b.name.toLowerCase().startsWith(needle) ? 0 : 1
        return ap - bp || a.name.localeCompare(b.name)
      })
      .slice(0, 10)
  }, [cities, query, stateOf])

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const choose = (slug: string) => {
    setCity(slug); setOpen(false); setQuery('')
  }

  return (
    <div ref={boxRef} className="relative w-full sm:w-auto">
      <button
        type="button"
        onClick={() => { setOpen((v) => !v); setActive(0) }}
        aria-haspopup="listbox" aria-expanded={open}
        className={`flex w-full items-center justify-between gap-3 rounded-full
                    border border-line bg-surface font-semibold text-ink
                    transition-colors hover:border-brand/50 sm:w-auto
                    ${compact ? 'px-3.5 py-2 text-xs' : 'px-5 py-3 text-sm'}`}
      >
        <span className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
               stroke="currentColor" strokeWidth="1.9" className="text-brand"
               aria-hidden="true">
            <path d="M12 21s7-5.3 7-11a7 7 0 1 0-14 0c0 5.7 7 11 7 11z" />
            <circle cx="12" cy="10" r="2.6" />
          </svg>
          {city?.name ?? 'Choose a city'}
        </span>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none"
             stroke="currentColor" strokeWidth="2.2" className="text-faint"
             aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 w-full min-w-[17rem]
                        animate-float-in overflow-hidden rounded-2xl border
                        border-line bg-surface shadow-lift sm:w-80">
          <div className="border-b border-line p-2.5">
            <input
              autoFocus value={query}
              onChange={(e) => { setQuery(e.target.value); setActive(0) }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown') {
                  e.preventDefault()
                  setActive((i) => Math.min(i + 1, results.length - 1))
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault(); setActive((i) => Math.max(i - 1, 0))
                } else if (e.key === 'Enter' && results[active]) {
                  e.preventDefault(); choose(results[active].slug)
                } else if (e.key === 'Escape') { setOpen(false) }
              }}
              placeholder={`Search ${cities.length} cities or a state`}
              aria-label="Search cities" className="input py-2 text-sm" />
          </div>

          {!query && (
            <div className="flex flex-wrap gap-1.5 border-b border-line p-2.5">
              {QUICK.filter((slug) => cities.some((c) => c.slug === slug))
                .map((slug) => {
                  const match = cities.find((c) => c.slug === slug)!
                  return (
                    <button key={slug} type="button" onClick={() => choose(slug)}
                            className={`chip transition-colors hover:border-brand
                                        hover:text-brand ${
                              citySlug === slug ? 'border-brand text-brand' : ''}`}>
                      {match.name}
                    </button>
                  )
                })}
            </div>
          )}

          <ul role="listbox" className="max-h-64 overflow-y-auto py-1">
            {results.map((c, i) => (
              <li key={c.slug} role="option" aria-selected={citySlug === c.slug}>
                <button type="button" onClick={() => choose(c.slug)}
                        onMouseEnter={() => setActive(i)}
                        className={`flex w-full items-center justify-between px-3.5
                                    py-2 text-left text-sm transition-colors ${
                          i === active ? 'bg-brand-soft text-brand'
                                       : 'text-ink hover:bg-raised'}`}>
                  <span className="min-w-0">
                    <span className="block truncate">{c.name}</span>
                    <span className="block truncate text-2xs text-faint">
                      {stateOf.get(c.slug) ?? ''}</span>
                  </span>
                  {citySlug === c.slug && (
                    <span className="text-2xs font-semibold text-brand">current</span>
                  )}
                </button>
              </li>
            ))}
            {results.length === 0 && (
              <li className="px-3.5 py-6 text-center text-xs text-muted">
                No Indian city matches “{query}”.
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
