/** Design system: barra de progresso. */
import type { CSSProperties, ReactNode } from 'react'

interface ProgressBarProps {
  value?: number
  max?: number
  label?: ReactNode
  caption?: ReactNode
  color?: string
  /** Faixa em movimento: mostra que o trabalho continua entre um avanço e outro. */
  animada?: boolean
  style?: CSSProperties
}

export function ProgressBar({ value = 0, max = 100, label, caption, color, animada = false, style }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="progress" style={style}>
      {(label || caption) && (
        <div className="progress-labels">
          <span>{label}</span>
          <span className="progress-caption">{caption}</span>
        </div>
      )}
      <div
        className="progress-track"
        role="progressbar"
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={typeof label === 'string' ? label : undefined}
      >
        <div className={`progress-fill${animada ? ' progress-fill-viva' : ''}`} style={{ width: `${pct}%`, ...(color ? { background: color } : null) }} />
      </div>
    </div>
  )
}
