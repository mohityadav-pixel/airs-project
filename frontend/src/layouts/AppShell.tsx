import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

import { DataModeBanner } from '@/components/DataModeBanner'
import { Logo } from '@/components/Logo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuth } from '@/lib/auth'
import type { ReactNode } from 'react'

interface NavItem { to: string; label: string; minRole?: 'official' }

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/map', label: 'Live Map' },
  { to: '/predictions', label: 'Predictions' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/simulator', label: 'Simulator' },
  { to: '/copilot', label: 'AI Copilot' },
  { to: '/command-center', label: 'Command Center', minRole: 'official' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, hasRole } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => { setMenuOpen(false) }, [location.pathname])

  const visible = NAV.filter((item) => !item.minRole || hasRole(item.minRole))

  return (
    <div className="flex min-h-full flex-col bg-canvas">
      <DataModeBanner />

      <header className="sticky top-0 z-40 border-b border-line
                         bg-surface/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-4 px-4 sm:px-6">
          <Link to="/" className="shrink-0" aria-label="AIRS home">
            <Logo />
          </Link>

          <nav aria-label="Main" className="hidden flex-1 items-center gap-0.5 lg:flex">
            {visible.map((item) => (
              <NavLink key={item.to} to={item.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? 'bg-brand/10 text-brand'
                             : 'text-muted hover:bg-raised hover:text-ink'}`}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            {user ? (
              <div className="hidden items-center gap-2 sm:flex">
                <div className="text-right leading-tight">
                  <p className="text-xs font-medium text-ink">{user.full_name}</p>
                  <p className="text-2xs capitalize text-faint">{user.role}</p>
                </div>
                <button type="button" onClick={logout}
                        className="btn-subtle px-2.5 py-1.5 text-xs">Sign out</button>
              </div>
            ) : (
              <Link to="/login" className="btn-ghost hidden px-3 py-1.5 text-xs sm:inline-flex">
                Sign in
              </Link>
            )}
            <button type="button" onClick={() => setMenuOpen((v) => !v)}
                    aria-expanded={menuOpen} aria-controls="mobile-nav"
                    aria-label="Menu"
                    className="btn-subtle h-9 w-9 p-0 lg:hidden">
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
            {visible.map((item) => (
              <NavLink key={item.to} to={item.to}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2.5 text-sm font-medium ${
                    isActive ? 'bg-brand/10 text-brand' : 'text-muted'}`}>
                {item.label}
              </NavLink>
            ))}
            <div className="mt-2 border-t border-line pt-2">
              {user ? (
                <button type="button" onClick={logout}
                        className="block w-full rounded-lg px-3 py-2.5 text-left
                                   text-sm text-muted">
                  Sign out ({user.full_name})
                </button>
              ) : (
                <Link to="/login"
                      className="block rounded-lg px-3 py-2.5 text-sm text-muted">
                  Sign in
                </Link>
              )}
            </div>
          </nav>
        )}
      </header>

      <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-5 sm:px-6 sm:py-7">
        {children}
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-2 px-4 py-5 text-2xs
                        text-faint sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>AIRS — AI Response &amp; Intervention System.</p>
          <p className="max-w-xl sm:text-right">
            Forecasts, source attribution and simulations are model estimates.
            Health guidance is general public-health information, not medical advice.
          </p>
        </div>
      </footer>
    </div>
  )
}
