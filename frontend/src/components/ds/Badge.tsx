import type { CSSProperties, ReactNode } from 'react'

type Tone = 'neutral' | 'brand' | 'pink' | 'success' | 'warning' | 'danger' | 'info'

const tones: Record<Tone, [string, string]> = {
  neutral: ['var(--np-surface-sunken)', 'var(--np-text-muted)'],
  brand: ['var(--np-purple-100)', 'var(--np-purple-700)'],
  pink: ['var(--np-pink-200)', 'var(--np-pink-600)'],
  success: ['var(--np-success-soft)', '#2a7342'],
  warning: ['var(--np-warning-soft)', '#8a5a06'],
  danger: ['var(--np-danger-soft)', 'var(--np-danger)'],
  info: ['var(--np-info-soft)', '#37618a'],
}

interface BadgeProps {
  tone?: Tone
  dot?: boolean
  children?: ReactNode
  style?: CSSProperties
}

export function Badge({ tone = 'neutral', dot = false, children, style }: BadgeProps) {
  const [bg, fg] = tones[tone]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--np-space-2)',
        background: bg,
        color: fg,
        borderRadius: 'var(--np-radius-pill)',
        padding: '3px 10px',
        font: 'var(--np-type-label)',
        fontSize: 'var(--np-text-xs)',
        ...style,
      }}
    >
      {dot && <i style={{ width: 6, height: 6, borderRadius: '50%', background: fg, display: 'inline-block' }} />}
      {children}
    </span>
  )
}
