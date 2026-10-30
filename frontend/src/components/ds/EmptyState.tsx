/** Design system: mensagem para listas vazias. */
import type { CSSProperties, ReactNode } from 'react'

interface EmptyStateProps {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
  style?: CSSProperties
}

export function EmptyState({ title, description, action, icon, style }: EmptyStateProps) {
  return (
    <div className="empty-state" style={style}>
      {icon && (
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <p className="empty-state-title">{title}</p>
      {description && <p className="empty-state-text">{description}</p>}
      {action}
    </div>
  )
}
