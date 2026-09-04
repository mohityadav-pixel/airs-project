import type { ReactNode } from 'react'

export function PageHeader({ title, description, actions, children }: {
  title: string
  description?: string
  actions?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 border-b border-line pb-4
                    sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
        )}
        {children}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}
