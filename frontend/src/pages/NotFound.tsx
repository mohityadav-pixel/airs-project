import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <p className="label-eyebrow">404</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        That page is not part of AIRS
      </h1>
      <p className="mt-2 text-sm text-muted">
        The link may be out of date. Everything starts from the dashboard.
      </p>
      <Link to="/dashboard" className="btn-primary mt-6">Go to the dashboard</Link>
    </div>
  )
}
