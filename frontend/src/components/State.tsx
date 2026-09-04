import type { ReactNode } from 'react'

import { ApiError } from '@/lib/api'

export function Skeleton({ className = '', style }:
  { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />
}

export function CardSkeleton({ lines = 3, title = true }:
  { lines?: number; title?: boolean }) {
  return (
    <div className="card card-pad" role="status" aria-busy="true"
         aria-label="Loading">
      {title && <Skeleton className="h-3.5 w-28 mb-4" />}
      <div className="space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={`h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
        ))}
      </div>
    </div>
  )
}

export function ChartSkeleton({ height = 240 }: { height?: number }) {
  return (
    <div className="card card-pad" role="status" aria-busy="true"
         aria-label="Loading chart">
      <Skeleton className="h-3.5 w-40 mb-4" />
      <Skeleton style={{ height }} className="w-full" />
    </div>
  )
}

export function ErrorState({ error, onRetry, compact = false }:
  { error: unknown; onRetry?: () => void; compact?: boolean }) {
  const message = error instanceof ApiError
    ? error.message
    : 'Something went wrong loading this data.'
  const isNetwork = error instanceof ApiError && error.code === 'network_error'
  const isConfig = error instanceof ApiError
    && ['provider_not_configured', 'provider_unavailable', 'ai_unavailable',
        'model_unavailable'].includes(error.code)

  return (
    <div className={`card ${compact ? 'p-4' : 'card-pad'} border-unhealthy/30`}
         role="alert">
      <div className="flex items-start gap-3">
        <span aria-hidden="true"
              className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full
                         bg-unhealthy/10 text-unhealthy text-xs font-bold">!</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ink">
            {isNetwork ? 'AIRS server unreachable'
              : isConfig ? 'This feature is not available right now'
              : 'Could not load this'}
          </p>
          <p className="mt-1 text-sm text-muted">{message}</p>
          {isNetwork && (
            <p className="mt-2 text-xs text-faint">
              Start it with <code className="font-mono">uvicorn app.main:app</code> in
              the <code className="font-mono">backend/</code> folder.
            </p>
          )}
          {onRetry && (
            <button type="button" onClick={onRetry}
                    className="btn-ghost mt-3 px-3 py-1.5 text-xs">Try again</button>
          )}
        </div>
      </div>
    </div>
  )
}

export function EmptyState({ title, description, action }:
  { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="card card-pad text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1.5 max-w-md text-sm text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
