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
    <div
      style={{
        display: 'grid',
        justifyItems: 'center',
        gap: 'var(--np-space-3)',
        textAlign: 'center',
        padding: 'var(--np-space-10) var(--np-space-6)',
        background: 'var(--np-surface-alt)',
        border: '1px dashed var(--np-border-brand)',
        borderRadius: 'var(--np-radius-lg)',
        ...style,
      }}
    >
      {icon && <span style={{ color: 'var(--np-text-brand)', opacity: 0.85 }}>{icon}</span>}
      <p style={{ margin: 0, font: 'var(--np-type-section)', color: 'var(--np-text-brand)' }}>{title}</p>
      {description && (
        <p style={{ margin: 0, maxWidth: 380, font: 'var(--np-type-body)', fontSize: 'var(--np-text-sm)', color: 'var(--np-text-muted)' }}>
          {description}
        </p>
      )}
      {action}
    </div>
  )
}
