import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { DataModeBanner } from '@/components/DataModeBanner'
import { Logo } from '@/components/Logo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuth } from '@/lib/auth'

/** The page is one scroll, so the primary nav is jump links, not routes. */
const SECTIONS = [
  { id: 'live', label: 'Live' },
  { id: 'history', label: 'History' },
  { id: 'forecast', label: 'Forecast' },
  { id: 'why', label: 'Why' },
  { id: 'solutions', label: 'Solutions' },
  { id: 'india', label: 'India map' },
]

const PAGES: Array<{ to: string; label: string; minRole?: 'official' }> = [
  { to: '/simulator', label: 'Simulator' },
  { to: '/command-center', label: 'Command Center', minRole: 'official' },
]

function useActiveSection(enabled: boolean) {
  const [active, setActive] = useState('live')
  useEffect(() => {
    if (!enabled) return
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setActive(visible.target.id)
      },
      // Bias the band towards the upper half so a section counts as "current"
      // once its heading is comfortably on screen, not when it fills the view.
      { rootMargin: '-15% 0px -55% 0px', threshold: [0.05, 0.3, 0.6] })
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [enabled])
  return active
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, hasRole } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const onHome = location.pathname === '/'
  const active = useActiveSection(onHome)

  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  const pages = PAGES.filter((p) => !p.minRole || hasRole(p.minRole))

  return (
    <div className="flex min-h-full flex-col bg-canvas">
      <DataModeBanner />

      <header className="sticky top-0 z-40 border-b border-line bg-canvas/90
                         backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-content items-center gap-4 px-4 sm:px-6">
          <Link to="/" className="shrink-0" aria-label="AIRS home"><Logo /></Link>

          <nav aria-label="Sections"
               className="hidden flex-1 items-center gap-0.5 lg:flex">
            {onHome && SECTIONS.map((s) => (
              <a key={s.id} href={`#${s.id}`}
                 aria-current={active === s.id ? 'true' : undefined}
                 className={`rounded-full px-3 py-2 text-sm font-semibold
                             transition-colors ${
                   active === s.id ? 'bg-brand-soft text-brand'
                                   : 'text-muted hover:text-brand'}`}>
                {s.label}
              </a>
            ))}
            {!onHome && (
              <Link to="/" className="rounded-full px-3 py-2 text-sm font-semibold
                                      text-muted hover:text-brand">
                ← Back to the dashboard
              </Link>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <div className="hidden items-center gap-1 md:flex">
              {pages.map((p) => (
                <NavLink key={p.to} to={p.to}
                  className={({ isActive }) =>
                    `rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                      isActive ? 'bg-brand text-white'
                               : 'border border-line text-muted hover:border-brand/50 hover:text-brand'}`}>
                  {p.label}
                </NavLink>
              ))}
            </div>
            <ThemeToggle />
            {user ? (
              <button type="button" onClick={logout}
                      className="btn-subtle hidden py-1.5 text-xs sm:inline-flex">
                Sign out
              </button>
            ) : (
              <Link to="/login"
                    className="btn-ghost hidden px-4 py-1.5 text-xs sm:inline-flex">
                Sign in
              </Link>
            )}
            <button type="button" onClick={() => setMenuOpen((v) => !v)}
                    aria-expanded={menuOpen} aria-controls="mobile-nav"
                    aria-label="Menu"
                    className="btn-subtle h-9 w-9 rounded-full p-0 lg:hidden">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                   aria-hidden="true">
                {menuOpen ? <path d="M6 6l12 12M18 6L6 18" />
                          : <path d="M4 7h16M4 12h16M4 17h16" />}
              </svg>
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav id="mobile-nav" aria-label="Mobile"
               className="border-t border-line bg-surface px-3 py-2 lg:hidden">
            {onHome && SECTIONS.map((s) => (
              <a key={s.id} href={`#${s.id}`}
                 onClick={() => setMenuOpen(false)}
                 className="block rounded-xl px-3 py-2.5 text-sm font-semibold
                            text-muted hover:bg-raised hover:text-brand">
                {s.label}
              </a>
            ))}
            <div className="mt-1 border-t border-line pt-1">
              {pages.map((p) => (
                <NavLink key={p.to} to={p.to}
                         className="block rounded-xl px-3 py-2.5 text-sm font-semibold
                                    text-muted hover:bg-raised hover:text-brand">
                  {p.label}
                </NavLink>
              ))}
              {user ? (
                <button type="button" onClick={logout}
                        className="block w-full rounded-xl px-3 py-2.5 text-left
                                   text-sm font-semibold text-muted">
                  Sign out ({user.full_name})
                </button>
              ) : (
                <Link to="/login"
                      className="block rounded-xl px-3 py-2.5 text-sm font-semibold
                                 text-muted">Sign in</Link>
              )}
            </div>
          </nav>
        )}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-content px-4 py-8 sm:px-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start
                          sm:justify-between">
            <div>
              <Logo />
              <p className="mt-2 max-w-sm text-2xs leading-relaxed text-faint">
                Air quality from the WAQI network and OpenWeatherMap, forecast by
                AIRS's own model, explained in plain language.
              </p>
            </div>
            <p className="max-w-md text-2xs leading-relaxed text-faint sm:text-right">
              Forecasts, source attribution and simulations are model estimates,
              not guarantees. Health guidance is general public-health information
              and not medical advice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
