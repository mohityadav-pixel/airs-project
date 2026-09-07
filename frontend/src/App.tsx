import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { ChatWidget } from '@/components/ChatWidget'
import { CardSkeleton } from '@/components/State'
import { AppShell } from '@/layouts/AppShell'
import { useAuth } from '@/lib/auth'
import type { Role } from '@/lib/types'
import Home from '@/pages/Home'

// The one-page dashboard is the product; the two working tools stay as their
// own routes because nobody wants a simulator to scroll past them.
const Simulator = lazy(() => import('@/pages/Simulator'))
const CommandCenter = lazy(() => import('@/pages/CommandCenter'))
const Login = lazy(() => import('@/pages/Login'))
const Register = lazy(() => import('@/pages/Register'))

function PageFallback() {
  return (
    <div className="mx-auto grid max-w-content gap-4 px-4 py-8 sm:px-6
                    lg:grid-cols-3">
      {[0, 1, 2].map((i) => <CardSkeleton key={i} lines={4} />)}
    </div>
  )
}

function RequireRole({ role, children }: { role: Role; children: React.ReactNode }) {
  const { user, loading, hasRole } = useAuth()
  const location = useLocation()

  if (loading) return <PageFallback />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (!hasRole(role)) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <h2 className="text-base font-bold text-ink">
          This area needs the {role} role
        </h2>
        <p className="mt-2 text-sm text-muted">
          The Command Center is for city officials. Your account is a{' '}
          {user.role}; an administrator can change that.
        </p>
      </div>
    )
  }
  return <>{children}</>
}

function Padded({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-content px-4 py-8 sm:px-6">{children}</div>
  )
}

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/simulator" element={<Padded><Simulator /></Padded>} />
          <Route path="/command-center" element={
            <Padded>
              <RequireRole role="official"><CommandCenter /></RequireRole>
            </Padded>} />
          <Route path="/login" element={<Padded><Login /></Padded>} />
          <Route path="/register" element={<Padded><Register /></Padded>} />
          {/* The old multi-page routes now live as sections of the one page. */}
          <Route path="/dashboard" element={<Navigate to="/#live" replace />} />
          <Route path="/map" element={<Navigate to="/#india" replace />} />
          <Route path="/predictions" element={<Navigate to="/#forecast" replace />} />
          <Route path="/analytics" element={<Navigate to="/#history" replace />} />
          <Route path="/copilot" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
      <ChatWidget />
    </AppShell>
  )
}
