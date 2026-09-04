import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { CardSkeleton } from '@/components/State'
import { AppShell } from '@/layouts/AppShell'
import { useAuth } from '@/lib/auth'
import type { Role } from '@/lib/types'
import Landing from '@/pages/Landing'

// Route-level code splitting: the landing page must not download the map, the
// charting library and the command centre before it can paint.
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const MapPage = lazy(() => import('@/pages/MapPage'))
const Predictions = lazy(() => import('@/pages/Predictions'))
const Analytics = lazy(() => import('@/pages/Analytics'))
const Simulator = lazy(() => import('@/pages/Simulator'))
const Copilot = lazy(() => import('@/pages/Copilot'))
const CommandCenter = lazy(() => import('@/pages/CommandCenter'))
const Login = lazy(() => import('@/pages/Login'))
const Register = lazy(() => import('@/pages/Register'))
const NotFound = lazy(() => import('@/pages/NotFound'))

function RequireRole({ role, children }:
  { role: Role; children: React.ReactNode }) {
  const { user, loading, hasRole } = useAuth()
  const location = useLocation()

  if (loading) return <PageFallback />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (!hasRole(role)) {
    return (
      <div className="card card-pad mx-auto max-w-lg text-center">
        <h2 className="text-base font-semibold text-ink">
          You need the {role} role
        </h2>
        <p className="mt-2 text-sm text-muted">
          The City Command Center is restricted to city officials and
          administrators. Your account is currently a {user.role}. An
          administrator can change this from the user list.
        </p>
      </div>
    )
  }
  return <>{children}</>
}

function PageFallback() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} lines={4} />)}
    </div>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <Suspense fallback={<PageFallback />}>{children}</Suspense>
    </AppShell>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Shell><Dashboard /></Shell>} />
      <Route path="/map" element={<Shell><MapPage /></Shell>} />
      <Route path="/predictions" element={<Shell><Predictions /></Shell>} />
      <Route path="/analytics" element={<Shell><Analytics /></Shell>} />
      <Route path="/simulator" element={<Shell><Simulator /></Shell>} />
      <Route path="/copilot" element={<Shell><Copilot /></Shell>} />
      <Route path="/command-center" element={
        <Shell><RequireRole role="official"><CommandCenter /></RequireRole></Shell>} />
      <Route path="/login" element={<Shell><Login /></Shell>} />
      <Route path="/register" element={<Shell><Register /></Shell>} />
      <Route path="*" element={<Shell><NotFound /></Shell>} />
    </Routes>
  )
}
