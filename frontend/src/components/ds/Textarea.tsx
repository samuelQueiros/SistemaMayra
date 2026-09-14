import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'

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
}: TextareaProps) {
  return (
    <label style={{ display: 'grid', gap: 'var(--np-space-2)', ...style }}>
      {label && <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)' }}>{label}</span>}
      <textarea
        id={id}
        rows={rows}
        value={value}
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={disabled}
        required={required}
        onChange={onChange}
        style={{
          padding: 'var(--np-space-3) var(--np-field-pad-x)',
          background: disabled ? 'var(--np-surface-sunken)' : 'var(--np-surface)',
          border: '1px solid var(--np-border-strong)',
          borderRadius: 'var(--np-radius-sm)',
          font: 'var(--np-type-body)',
          color: 'var(--np-text)',
          resize: 'vertical',
          outline: 'none',
        }}
      />
      {(hint || maxLength) && (
        <span style={{ display: 'flex', justifyContent: 'space-between', font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>
          <span>{hint}</span>
          {maxLength && (
            <span>
              {(value || '').length}/{maxLength}
            </span>
          )}
        </span>
      )}
    </label>
  )
}
