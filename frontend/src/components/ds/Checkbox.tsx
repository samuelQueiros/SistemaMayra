/** Design system: caixa de marcação com rótulo. */
import type { CSSProperties, ChangeEventHandler, ReactNode } from 'react'
import { Check } from 'lucide-react'

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
    <label className="checkbox" data-disabled={disabled || undefined} style={style}>
      <span className="checkbox-box" data-checked={checked || undefined}>
        {checked && <Check aria-hidden="true" />}
        <input type="checkbox" checked={checked} disabled={disabled} onChange={onChange} />
      </span>
      {label && (
        <span>
          <span className="checkbox-label">{label}</span>
          {description && <span className="checkbox-description">{description}</span>}
        </span>
      )}
    </label>
  )
}
