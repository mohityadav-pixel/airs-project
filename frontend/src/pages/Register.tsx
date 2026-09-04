import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { api, ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useSelection } from '@/lib/selection'

export default function Register() {
  const { user, register } = useAuth()
  const { cities } = useSelection()
  const navigate = useNavigate()
  const groups = useQuery({ queryKey: ['health-groups'], queryFn: api.healthGroups,
    staleTime: 3_600_000 })

  const [form, setForm] = useState({
    full_name: '', email: '', password: '', home_city_slug: '',
    sensitivity_group: 'general',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/dashboard" replace />

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password.length < 10) {
      setError('Please use a password of at least 10 characters.')
      return
    }
    setBusy(true); setError(null)
    try {
      await register({
        ...form,
        home_city_slug: form.home_city_slug || undefined,
      })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  const set = (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [key]: e.target.value }))

  return (
    <div className="mx-auto max-w-sm py-8">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        Create an AIRS account
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        New accounts are citizen accounts. Analyst, official and administrator
        roles are granted by an administrator — they cannot be self-selected.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="name" className="mb-1.5 block text-xs font-medium text-ink">
            Full name</label>
          <input id="name" required value={form.full_name}
                 onChange={set('full_name')} className="input" autoComplete="name" />
        </div>
        <div>
          <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-ink">
            Email</label>
          <input id="email" type="email" required value={form.email}
                 onChange={set('email')} className="input" autoComplete="email" />
        </div>
        <div>
          <label htmlFor="password"
                 className="mb-1.5 block text-xs font-medium text-ink">Password</label>
          <input id="password" type="password" required minLength={10}
                 value={form.password} onChange={set('password')} className="input"
                 autoComplete="new-password" aria-describedby="pw-hint" />
          <p id="pw-hint" className="mt-1 text-2xs text-faint">
            At least 10 characters.</p>
        </div>
        <div>
          <label htmlFor="city" className="mb-1.5 block text-xs font-medium text-ink">
            Home city</label>
          <select id="city" value={form.home_city_slug}
                  onChange={set('home_city_slug')} className="input">
            <option value="">Choose later</option>
            {cities.map((c) => (
              <option key={c.slug} value={c.slug}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="group" className="mb-1.5 block text-xs font-medium text-ink">
            Health profile</label>
          <select id="group" value={form.sensitivity_group}
                  onChange={set('sensitivity_group')} className="input"
                  aria-describedby="group-hint">
            {(groups.data ?? [{ key: 'general', label: 'General population' }])
              .map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
          </select>
          <p id="group-hint" className="mt-1 text-2xs text-faint">
            Used only to tailor public-health guidance. AIRS is not a medical device.
          </p>
        </div>

        {error && (
          <p role="alert"
             className="rounded-xl border border-unhealthy/30 bg-unhealthy/10 px-3
                        py-2.5 text-xs text-unhealthy">{error}</p>
        )}

        <button type="submit" disabled={busy} className="btn-primary w-full">
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-5 text-xs text-muted">
        Already have an account? <Link to="/login" className="text-brand">Sign in</Link>
      </p>
    </div>
  )
}
