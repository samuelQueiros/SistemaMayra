/** Design system: campo de texto com rótulo e mensagem de erro. */
import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'
import { useId } from 'react'
import { CircleAlert } from 'lucide-react'

interface InputProps {
  id?: string
  label?: ReactNode
  hint?: ReactNode
  error?: ReactNode
  value?: string | number
  placeholder?: string
  type?: string
  min?: number
  max?: number
  step?: string | number
  /** Ícone à esquerda (ex.: lupa da busca). */
  prefix?: ReactNode
  /** Elemento à direita, dentro do campo (ex.: botão de mostrar a senha). */
  suffix?: ReactNode
  autoComplete?: string
  disabled?: boolean
  readOnly?: boolean
  required?: boolean
  onChange?: ChangeEventHandler<HTMLInputElement>
  style?: CSSProperties
  list?: string
  'aria-label'?: string
}

export function Input({
  id,
  label,
  hint,
  error,
  value,
  placeholder,
  type = 'text',
  min,
  max,
  step,
  prefix,
  suffix,
  autoComplete,
  disabled = false,
  readOnly = false,
  required = false,
  onChange,
  style,
  list,
  'aria-label': ariaLabel,
}: InputProps) {
  const auto = useId()
  const inputId = id ?? auto
  const idAjuda = `${inputId}-ajuda`
  const ajuda = error || hint
  const comum = {
    id: inputId,
    type,
    value,
    placeholder,
    min,
    max,
    step,
    disabled,
    readOnly,
    required,
    onChange,
    list,
    autoComplete,
    'aria-label': ariaLabel,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': ajuda ? idAjuda : undefined,
  }
  return (
    <div className="field" style={style}>
      {label && (
        <label className="field-label" htmlFor={inputId}>
          {label}
          {required && (
            <i className="field-required" aria-hidden="true">
              *
            </i>
          )}
        </label>
      )}
      {prefix || suffix ? (
        <span className="control" data-invalid={error ? 'true' : undefined} data-disabled={disabled || readOnly ? 'true' : undefined}>
          {prefix && (
            <span className="control-prefix" aria-hidden="true">
              {prefix}
            </span>
          )}
          <input {...comum} />
          {suffix && <span className="control-suffix">{suffix}</span>}
        </span>
      ) : (
        <input className="input" {...comum} />
      )}
      {error ? (
        <span className="field-error" id={idAjuda}>
          <CircleAlert aria-hidden="true" />
          {error}
        </span>
      ) : (
        hint && (
          <span className="field-hint" id={idAjuda}>
            {hint}
          </span>
        )
      )}
    </div>
  )
}
