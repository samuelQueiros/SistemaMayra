import type { CSSProperties, ReactNode } from 'react'

interface PageHeaderProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  meta?: ReactNode
  style?: CSSProperties
}

export function PageHeader({ eyebrow, title, description, actions, meta, style }: PageHeaderProps) {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: 'var(--np-space-6)',
        flexWrap: 'wrap',
        marginBottom: 'var(--np-space-6)',
        ...style,
      }}
    >
      <div style={{ minWidth: 0 }}>
        {eyebrow && (
          <p
            style={{
              margin: '0 0 var(--np-space-2)',
              font: 'var(--np-type-overline)',
              letterSpacing: 'var(--np-tracking-caps)',
              textTransform: 'uppercase',
              color: 'var(--np-secondary)',
            }}
          >
            {eyebrow}
          </p>
        )}
        <h1 style={{ margin: 0, font: 'var(--np-type-display)', fontSize: 'var(--np-text-2xl)', color: 'var(--np-text)' }}>{title}</h1>
        {description && <p style={{ margin: 'var(--np-space-2) 0 0', maxWidth: 620, font: 'var(--np-type-body)', color: 'var(--np-text-muted)' }}>{description}</p>}
        {meta && <div style={{ display: 'flex', gap: 'var(--np-space-3)', marginTop: 'var(--np-space-3)', flexWrap: 'wrap' }}>{meta}</div>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 'var(--np-space-3)', flexWrap: 'wrap' }}>{actions}</div>}
    </header>
  )
}
