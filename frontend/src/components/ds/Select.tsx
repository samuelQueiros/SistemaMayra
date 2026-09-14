import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'

interface Option {
  value: string
  label: string
}

interface SelectProps {
  id?: string
  label?: ReactNode
  hint?: ReactNode
  value?: string
  options?: Option[]
  placeholder?: string
  disabled?: boolean
  required?: boolean
  onChange?: ChangeEventHandler<HTMLSelectElement>
  style?: CSSProperties
}

export function Select({
  id,
  label,
  hint,
  value,
  options = [],
  placeholder = 'Selecione',
  disabled = false,
  required = false,
  onChange,
  style,
}: SelectProps) {
  return (
    <label style={{ display: 'grid', gap: 'var(--np-space-2)', ...style }}>
      {label && <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)' }}>{label}</span>}
      <span style={{ position: 'relative', display: 'block' }}>
        <select
          id={id}
          value={value}
          disabled={disabled}
          required={required}
          onChange={onChange}
          style={{
            width: '100%',
            height: 'var(--np-control-h)',
            padding: '0 var(--np-space-8) 0 var(--np-field-pad-x)',
            appearance: 'none',
            background: disabled ? 'var(--np-surface-sunken)' : 'var(--np-surface)',
            border: '1px solid var(--np-border-strong)',
            borderRadius: 'var(--np-radius-sm)',
            font: 'var(--np-type-body)',
            color: 'var(--np-text)',
            outline: 'none',
          }}
        >
          <option value="">{placeholder}</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <i
          aria-hidden
          style={{
            position: 'absolute',
            right: 14,
            top: '50%',
            width: 8,
            height: 8,
            marginTop: -6,
            borderRight: '2px solid var(--np-purple-600)',
            borderBottom: '2px solid var(--np-purple-600)',
            transform: 'rotate(45deg)',
            pointerEvents: 'none',
          }}
        />
      </span>
      {hint && <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>{hint}</span>}
    </label>
  )
}
