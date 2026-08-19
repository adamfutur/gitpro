import type { ReactNode } from 'react'
import './EmptyState.css'

export default function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="gc-empty">
      <h3 className="gc-empty-title">{title}</h3>
      {description && <p className="gc-empty-desc">{description}</p>}
      {action && <div className="gc-empty-action">{action}</div>}
    </div>
  )
}
