import type { CSSProperties, MouseEventHandler, ReactNode } from 'react'

type Variant = 'ghost' | 'soft' | 'outline'
type Size = 'sm' | 'md' | 'lg'

interface IconButtonProps {
  label: string
  icon: ReactNode
  variant?: Variant
  size?: Size
  disabled?: boolean
  onClick?: MouseEventHandler<HTMLButtonElement>
  style?: CSSProperties
}

export function IconButton({ label, icon, variant = 'ghost', size = 'md', disabled = false, onClick, style }: IconButtonProps) {
  const dim = size === 'sm' ? 'var(--np-control-h-sm)' : size === 'lg' ? 'var(--np-control-h-lg)' : 'var(--np-control-h)'
  const skin: Record<Variant, CSSProperties> = {
    ghost: { background: 'transparent', color: 'var(--np-text-muted)', border: '1px solid transparent' },
    soft: { background: 'var(--np-surface-alt)', color: 'var(--np-text-brand)', border: '1px solid transparent' },
    outline: { background: 'var(--np-surface)', color: 'var(--np-text-brand)', border: '1px solid var(--np-border)' },
  }
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: dim,
        height: dim,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--np-radius-pill)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        transition: 'background var(--np-dur) var(--np-ease)',
        ...skin[variant],
        ...style,
      }}
    >
      {icon}
    </button>
  )
}
