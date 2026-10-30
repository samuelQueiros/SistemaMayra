/** Design system: botão só com ícone. */
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { buttonClass } from './buttonClass'
import type { ButtonSize } from './buttonClass'

type Variant = 'ghost' | 'secondary' | 'tonal' | 'danger-ghost'

interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'aria-label'> {
  /** Obrigatório: é o nome acessível do botão (aria-label) e a dica (title). */
  label: string
  icon: ReactNode
  variant?: Variant
  /** md = 44×44 (padrão); sm = 36×36 só dentro de tabelas. */
  size?: ButtonSize
}

export function IconButton({ label, icon, variant = 'ghost', size = 'md', type = 'button', className, ...rest }: IconButtonProps) {
  return (
    <button type={type} aria-label={label} title={label} className={buttonClass(variant, size, ['btn-icon', className].filter(Boolean).join(' '))} {...rest}>
      {icon}
    </button>
  )
}
