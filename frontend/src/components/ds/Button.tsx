import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { buttonClass } from './buttonClass'
import type { ButtonSize, ButtonVariant } from './buttonClass'

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant
  /** sm = 36px (tabelas), md = 44px (padrão), lg = 52px (ação principal do topo). */
  size?: ButtonSize
  icon?: ReactNode
  iconRight?: ReactNode
  fullWidth?: boolean
  /** Mostra o spinner, desabilita o botão e troca o texto por `loadingLabel`. */
  loading?: boolean
  loadingLabel?: ReactNode
  children?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  fullWidth = false,
  loading = false,
  loadingLabel,
  disabled = false,
  type = 'button',
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, size, [fullWidth && 'btn-block', className].filter(Boolean).join(' '))}
      {...rest}
    >
      {loading ? <span className="btn-spinner" aria-hidden="true" /> : icon}
      {loading ? (loadingLabel ?? children) : children}
      {!loading && iconRight}
    </button>
  )
}
