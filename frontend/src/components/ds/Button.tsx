import type { CSSProperties, MouseEventHandler, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const variants: Record<Variant, CSSProperties> = {
  primary: {
    background: 'var(--np-primary)',
    color: 'var(--np-text-on-brand)',
    border: '1px solid var(--np-primary)',
    boxShadow: 'var(--np-shadow-sm)',
  },
  secondary: {
    background: 'var(--np-secondary)',
    color: 'var(--np-white)',
    border: '1px solid var(--np-secondary)',
    boxShadow: 'var(--np-shadow-sm)',
  },
  outline: {
    background: 'var(--np-surface)',
    color: 'var(--np-text-brand)',
    border: '1px solid var(--np-border-brand)',
    boxShadow: 'var(--np-shadow-xs)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--np-text-brand)',
    border: '1px solid transparent',
    boxShadow: 'none',
  },
  danger: {
    background: 'var(--np-danger)',
    color: 'var(--np-white)',
    border: '1px solid var(--np-danger)',
    boxShadow: 'var(--np-shadow-sm)',
  },
}

const sizes: Record<Size, CSSProperties> = {
  sm: { height: 'var(--np-control-h-sm)', padding: '0 var(--np-space-3)', fontSize: 'var(--np-text-sm)' },
  md: { height: 'var(--np-control-h)', padding: '0 var(--np-space-5)', fontSize: 'var(--np-text-base)' },
  lg: { height: 'var(--np-control-h-lg)', padding: '0 var(--np-space-6)', fontSize: 'var(--np-text-md)' },
}

interface ButtonProps {
  variant?: Variant
  size?: Size
  icon?: ReactNode
  iconRight?: ReactNode
  fullWidth?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  onClick?: MouseEventHandler<HTMLButtonElement>
  children?: ReactNode
  style?: CSSProperties
}

// Exportado para estilizar elementos que não podem ser um <button> (ex.:
// <Link> do react-router-dom usado como ação de navegação com cara de botão).
export function buttonStyle(variant: Variant = 'primary', size: Size = 'md'): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--np-space-2)',
    borderRadius: 'var(--np-radius-pill)',
    fontFamily: 'var(--np-font-body)',
    fontWeight: 'var(--np-weight-bold)',
    textDecoration: 'none',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'background var(--np-dur) var(--np-ease), transform var(--np-dur-fast) var(--np-ease)',
    ...sizes[size],
    ...variants[variant],
  }
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  fullWidth = false,
  disabled = false,
  type = 'button',
  onClick,
  children,
  style,
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--np-space-2)',
        borderRadius: 'var(--np-radius-pill)',
        fontFamily: 'var(--np-font-body)',
        fontWeight: 'var(--np-weight-bold)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        width: fullWidth ? '100%' : 'auto',
        whiteSpace: 'nowrap',
        transition: 'background var(--np-dur) var(--np-ease), transform var(--np-dur-fast) var(--np-ease)',
        ...sizes[size],
        ...variants[variant],
        ...style,
      }}
    >
      {icon}
      {children}
      {iconRight}
    </button>
  )
}
