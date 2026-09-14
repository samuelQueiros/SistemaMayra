import type { CSSProperties, ReactNode } from 'react'

type Tone = 'plain' | 'brand' | 'sunken'

const tones: Record<Tone, CSSProperties> = {
  plain: { background: 'var(--np-surface)', border: '1px solid var(--np-border)' },
  brand: { background: 'var(--np-surface-alt)', border: '1px solid var(--np-border-brand)' },
  sunken: { background: 'var(--np-surface-sunken)', border: '1px solid var(--np-border)' },
}

interface CardProps {
  id?: string
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  tone?: Tone
  padding?: string
  children?: ReactNode
  style?: CSSProperties
}

export function Card({ id, title, subtitle, action, tone = 'plain', padding = 'var(--np-card-pad)', children, style }: CardProps) {
  return (
    <section id={id} style={{ borderRadius: 'var(--np-radius-lg)', boxShadow: 'var(--np-shadow-sm)', overflow: 'hidden', ...tones[tone], ...style }}>
      {(title || action) && (
        <header
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--np-space-4)',
            padding: `${padding} ${padding} 0`,
          }}
        >
          <div style={{ minWidth: 0 }}>
            {title && <h3 style={{ margin: 0, font: 'var(--np-type-section)', color: 'var(--np-text)' }}>{title}</h3>}
            {subtitle && <p style={{ margin: '2px 0 0', font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div style={{ padding }}>{children}</div>
    </section>
  )
}
