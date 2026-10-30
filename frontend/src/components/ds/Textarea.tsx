/** Design system: campo de texto com várias linhas. */
import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'
import { useId } from 'react'

interface TextareaProps {
  id?: string
  label?: ReactNode
  hint?: ReactNode
  value?: string
  placeholder?: string
  rows?: number
  maxLength?: number
  disabled?: boolean
  required?: boolean
  onChange?: ChangeEventHandler<HTMLTextAreaElement>
  style?: CSSProperties
  'aria-label'?: string
}

export function Textarea({
  id,
  label,
  hint,
  value,
  placeholder,
  rows = 4,
  maxLength,
  disabled = false,
  required = false,
  onChange,
  style,
  'aria-label': ariaLabel,
}: TextareaProps) {
  const auto = useId()
  const textareaId = id ?? auto
  const temRodape = Boolean(hint || maxLength)
  return (
    <div className="field" style={style}>
      {label && (
        <label className="field-label" htmlFor={textareaId}>
          {label}
          {required && (
            <i className="field-required" aria-hidden="true">
              *
            </i>
          )}
        </label>
      )}
      <textarea
        id={textareaId}
        className="textarea"
        rows={rows}
        value={value}
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={disabled}
        required={required}
        onChange={onChange}
        aria-label={ariaLabel}
        aria-describedby={hint ? `${textareaId}-ajuda` : undefined}
      />
      {temRodape && (
        <span className="field-hint" style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--s-3)' }}>
          <span id={`${textareaId}-ajuda`}>{hint}</span>
          {maxLength && (
            <span>
              {(value || '').length}/{maxLength}
            </span>
          )}
        </span>
      )}
    </div>
  )
}
