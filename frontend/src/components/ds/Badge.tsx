import type { CSSProperties, ReactNode } from 'react'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'

interface BadgeProps {
  tone?: Tone
  dot?: boolean
  icon?: ReactNode
  children?: ReactNode
  style?: CSSProperties
}

// Etiqueta em pílula. O texto sempre diz o estado — a cor só reforça.
export function Badge({ tone = 'neutral', dot = false, icon, children, style }: BadgeProps) {
  return (
    <span className={`badge badge-${tone}`} style={style}>
      {dot && <i className="badge-dot" aria-hidden="true" />}
      {icon}
      {children}
    </span>
  )
}
