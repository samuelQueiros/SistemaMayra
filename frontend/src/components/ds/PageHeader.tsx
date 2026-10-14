import type { CSSProperties, ReactNode } from 'react'

interface PageHeaderProps {
  /** Sobrelinha em caixa alta, violeta (ex.: "Pacientes"). */
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  meta?: ReactNode
  style?: CSSProperties
}

export function PageHeader({ eyebrow, title, description, actions, meta, style }: PageHeaderProps) {
  return (
    <header className="page-header" style={style}>
      <div className="page-header-text">
        {eyebrow && <p className="overline">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-subtitle">{description}</p>}
        {meta && <div className="page-header-meta">{meta}</div>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  )
}
