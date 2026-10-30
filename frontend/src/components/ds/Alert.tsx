/** Design system: caixa de aviso. */
import type { CSSProperties, ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const ICONES: Record<Tone, ReactNode> = {
  info: <Info aria-hidden="true" />,
  success: <CheckCircle2 aria-hidden="true" />,
  warning: <AlertTriangle aria-hidden="true" />,
  danger: <XCircle aria-hidden="true" />,
}

interface AlertProps {
  tone?: Tone
  title?: ReactNode
  /** Ícone próprio; por padrão cada tom tem o seu (status nunca só por cor). */
  icon?: ReactNode
  action?: ReactNode
  compact?: boolean
  children?: ReactNode
  style?: CSSProperties
}

export function Alert({ tone = 'info', title, icon, action, compact = false, children, style }: AlertProps) {
  return (
    <div role={tone === 'danger' ? 'alert' : 'status'} className={`alert alert-${tone}${compact ? ' alert-compact' : ''}`} style={style}>
      <span className="alert-icon">{icon ?? ICONES[tone]}</span>
      <div className="alert-content">
        {title && <p className="alert-title">{title}</p>}
        {children && <div className="alert-body">{children}</div>}
      </div>
      {action}
    </div>
  )
}
