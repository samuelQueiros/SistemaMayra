import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'

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
  prefix?: ReactNode
  disabled?: boolean
  required?: boolean
  onChange?: ChangeEventHandler<HTMLInputElement>
  style?: CSSProperties
  list?: string
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
  disabled = false,
  required = false,
  onChange,
  style,
  list,
}: InputProps) {
  return (
    <label style={{ display: 'grid', gap: 'var(--np-space-2)', ...style }}>
      {label && (
        <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)' }}>
          {label}
          {required && <i style={{ color: 'var(--np-secondary)', fontStyle: 'normal' }}> *</i>}
        </span>
      )}
      <span
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--np-space-2)',
          height: 'var(--np-control-h)',
          padding: '0 var(--np-field-pad-x)',
          background: disabled ? 'var(--np-surface-sunken)' : 'var(--np-surface)',
          border: `1px solid ${error ? 'var(--np-danger)' : 'var(--np-border-strong)'}`,
          borderRadius: 'var(--np-radius-sm)',
        }}
      >
        {prefix && <span style={{ color: 'var(--np-text-subtle)', display: 'inline-flex' }}>{prefix}</span>}
        <input
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          required={required}
          onChange={onChange}
          list={list}
          style={{
            border: 0,
            outline: 'none',
            background: 'transparent',
            width: '100%',
            font: 'var(--np-type-body)',
            color: 'var(--np-text)',
          }}
        />
      </span>
      {(error || hint) && (
        <span style={{ font: 'var(--np-type-caption)', color: error ? 'var(--np-danger)' : 'var(--np-text-subtle)' }}>{error || hint}</span>
      )}
    </label>
  )
}
