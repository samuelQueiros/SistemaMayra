import type { TemplateField } from '../api/types'
import { Input, Select, Textarea } from './ds'

type FieldValue = string | number | boolean | undefined

interface DynamicFieldProps {
  field: TemplateField
  value: FieldValue
  onChange: (value: FieldValue) => void
}

export default function DynamicField({ field, value, onChange }: DynamicFieldProps) {
  if (field.type === 'scale') {
    return (
      <Input
        id={field.key}
        label={field.label}
        type="number"
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        step="any"
        value={typeof value === 'number' ? value : ''}
        onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
        required
      />
    )
  }

  if (field.type === 'boolean') {
    return (
      <Select
        id={field.key}
        label={field.label}
        value={value === undefined ? '' : String(value)}
        options={[
          { value: 'true', label: 'Sim' },
          { value: 'false', label: 'Não' },
        ]}
        onChange={(e) => onChange(e.target.value === '' ? undefined : e.target.value === 'true')}
        required
      />
    )
  }

  if (field.type === 'select') {
    return (
      <Select
        id={field.key}
        label={field.label}
        value={typeof value === 'string' ? value : ''}
        options={(field.options ?? []).map((option) => ({ value: option, label: option }))}
        onChange={(e) => onChange(e.target.value === '' ? undefined : e.target.value)}
        required
      />
    )
  }

  return (
    <Textarea
      id={field.key}
      label={field.label}
      value={typeof value === 'string' ? value : ''}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
