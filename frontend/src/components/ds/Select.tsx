import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'
import { useId } from 'react'
import { ChevronDown } from 'lucide-react'

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
  const auto = useId()
  const selectId = id ?? auto
  return (
    <div className="field" style={style}>
      {label && (
        <label className="field-label" htmlFor={selectId}>
          {label}
          {required && (
            <i className="field-required" aria-hidden="true">
              *
            </i>
          )}
        </label>
      )}
      <span className="select-wrap">
        <select
          id={selectId}
          className="select"
          value={value}
          disabled={disabled}
          required={required}
          onChange={onChange}
          aria-describedby={hint ? `${selectId}-ajuda` : undefined}
        >
          <option value="">{placeholder}</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown className="select-chevron" aria-hidden="true" />
      </span>
      {hint && (
        <span className="field-hint" id={`${selectId}-ajuda`}>
          {hint}
        </span>
      )}
    </div>
  )
}
