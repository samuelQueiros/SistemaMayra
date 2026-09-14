import type { CSSProperties, ReactNode } from 'react'

interface ProgressBarProps {
  value?: number
  max?: number
  label?: ReactNode
  caption?: ReactNode
  color?: string
  style?: CSSProperties
}

export function ProgressBar({ value = 0, max = 100, label, caption, color = 'var(--np-primary)', style }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div style={{ display: 'grid', gap: 'var(--np-space-2)', ...style }}>
      {(label || caption) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', font: 'var(--np-type-label)', color: 'var(--np-text-muted)' }}>
          <span>{label}</span>
          <span style={{ color: 'var(--np-text-subtle)' }}>{caption}</span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemax={max}
        style={{ height: 10, borderRadius: 'var(--np-radius-pill)', background: 'var(--np-surface-sunken)', overflow: 'hidden' }}
      >
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 'var(--np-radius-pill)', background: color, transition: 'width var(--np-dur-slow) var(--np-ease)' }} />
      </div>
    </div>
  )
}
