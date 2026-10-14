import type { CSSProperties, ReactNode } from 'react'

type Tone = 'plain' | 'brand' | 'sunken'

interface CardProps {
  id?: string
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  tone?: Tone
  padding?: string
  children?: ReactNode
  style?: CSSProperties
  className?: string
}

export function Card({ id, title, subtitle, action, tone = 'plain', padding, children, style, className }: CardProps) {
  const pad = padding ? ({ '--card-pad': padding } as CSSProperties) : undefined
  return (
    <section id={id} className={['card', tone !== 'plain' && `card-${tone}`, className].filter(Boolean).join(' ')} style={{ ...pad, ...style }}>
      {(title || action) && (
        <header className="card-header">
          <div style={{ minWidth: 0 }}>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  )
}
