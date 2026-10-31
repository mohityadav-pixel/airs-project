import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) {
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname
    return <Navigate to={from ?? '/'} replace />
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await login(email, password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname
      navigate(from ?? '/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <h1 className="text-xl font-semibold tracking-tight text-ink">
        Sign in to AIRS
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Live air quality, forecasts and the simulator are open to everyone. Signing
        in saves your location and health profile; the Command Center additionally
        needs an official role.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-ink">
            Email
          </label>
          <input id="email" type="email" required autoComplete="email"
                 value={email} onChange={(e) => setEmail(e.target.value)}
                 className="input" />
        </div>
        <div>
          <label htmlFor="password"
                 className="mb-1.5 block text-xs font-medium text-ink">Password</label>
          <input id="password" type="password" required autoComplete="current-password"
                 value={password} onChange={(e) => setPassword(e.target.value)}
                 className="input" />
        </div>

        {error && (
          <p role="alert"
             className="rounded-xl border border-unhealthy/30 bg-unhealthy/10 px-3
                        py-2.5 text-xs text-unhealthy">{error}</p>
        )}

        <button type="submit" disabled={busy} className="btn-primary w-full">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="mt-5 text-xs text-muted">
        No account? <Link to="/register" className="text-brand">Create one</Link> —
        it takes a moment and gives you a citizen account.
      </p>
    </div>
  )
}
