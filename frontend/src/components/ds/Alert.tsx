import type { CSSProperties, ReactNode } from 'react'

type Tone = 'info' | 'success' | 'warning' | 'danger' | 'consent'

const tones: Record<Tone, [string, string, string]> = {
  info: ['var(--np-info-soft)', 'var(--np-info)', '#37618a'],
  success: ['var(--np-success-soft)', 'var(--np-success)', '#2a7342'],
  warning: ['var(--np-warning-soft)', 'var(--np-warning)', '#8a5a06'],
  danger: ['var(--np-danger-soft)', 'var(--np-danger)', 'var(--np-danger)'],
  consent: ['var(--np-pink-200)', 'var(--np-pink-500)', 'var(--np-pink-600)'],
}

interface AlertProps {
  tone?: Tone
  title?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  children?: ReactNode
  style?: CSSProperties
}

export function Alert({ tone = 'info', title, icon, action, children, style }: AlertProps) {
  const [bg, accent, fg] = tones[tone]
  return (
    <div
      role="status"
      style={{
        display: 'flex',
        gap: 'var(--np-space-3)',
        background: bg,
        border: `1px solid ${accent}`,
        borderRadius: 'var(--np-radius-md)',
        padding: 'var(--np-space-4)',
        ...style,
      }}
    >
      {icon && <span style={{ color: fg, display: 'inline-flex', flex: '0 0 auto' }}>{icon}</span>}
      <div style={{ flex: 1 }}>
        {title && <p style={{ margin: 0, font: 'var(--np-type-body-strong)', color: fg }}>{title}</p>}
        {children && (
          <div style={{ font: 'var(--np-type-body)', fontSize: 'var(--np-text-sm)', color: 'var(--np-text-muted)', marginTop: title ? 2 : 0 }}>
            {children}
          </div>
        )}
      </div>
      {action}
    </div>
  )
}
