import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'

interface CheckboxProps {
  label?: ReactNode
  description?: ReactNode
  checked?: boolean
  disabled?: boolean
  onChange?: ChangeEventHandler<HTMLInputElement>
  style?: CSSProperties
}

export function Checkbox({ label, description, checked = false, disabled = false, onChange, style }: CheckboxProps) {
  return (
    <label
      style={{
        display: 'flex',
        gap: 'var(--np-space-3)',
        alignItems: 'flex-start',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        ...style,
      }}
    >
      <span
        style={{
          width: 20,
          height: 20,
          flex: '0 0 auto',
          borderRadius: 'var(--np-radius-xs)',
          background: checked ? 'var(--np-primary)' : 'var(--np-surface)',
          border: `2px solid ${checked ? 'var(--np-primary)' : 'var(--np-border-strong)'}`,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all var(--np-dur) var(--np-ease)',
          position: 'relative',
        }}
      >
        {checked && (
          <i
            style={{
              width: 9,
              height: 5,
              borderLeft: '2px solid #fff',
              borderBottom: '2px solid #fff',
              transform: 'rotate(-45deg) translateY(-1px)',
            }}
          />
        )}
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={onChange}
          style={{ position: 'absolute', opacity: 0, width: '100%', height: '100%', margin: 0, cursor: 'inherit' }}
        />
      </span>
      {label && (
        <span>
          <span style={{ font: 'var(--np-type-body)', color: 'var(--np-text)' }}>{label}</span>
          {description && <span style={{ display: 'block', font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>{description}</span>}
        </span>
      )}
    </label>
  )
}
