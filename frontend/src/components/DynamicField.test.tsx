import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DynamicField from './DynamicField'
import type { TemplateField } from '../api/types'

describe('DynamicField', () => {
  it('campo scale chama onChange com um número', () => {
    const onChange = vi.fn()
    const field: TemplateField = { key: 'score', label: 'Pontuação', type: 'scale', min: 0, max: 4, weight: 1 }
    render(<DynamicField field={field} value={undefined} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText(/Pontuação/), { target: { value: '3' } })

    expect(onChange).toHaveBeenCalledWith(3)
  })

  it('campo boolean vira um select com Sim/Não e chama onChange com um booleano', () => {
    const onChange = vi.fn()
    const field: TemplateField = { key: 'presente', label: 'Está presente?', type: 'boolean', weight: 1 }
    render(<DynamicField field={field} value={undefined} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Está presente?'), { target: { value: 'true' } })

    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('campo select oferece as opções configuradas e chama onChange com o texto escolhido', () => {
    const onChange = vi.fn()
    const field: TemplateField = {
      key: 'intensidade',
      label: 'Intensidade',
      type: 'select',
      options: ['bastante', 'demais'],
      weight: 1,
    }
    render(<DynamicField field={field} value={undefined} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Intensidade'), { target: { value: 'demais' } })

    expect(onChange).toHaveBeenCalledWith('demais')
  })

  it('campo text vira uma textarea e chama onChange com o texto digitado', () => {
    const onChange = vi.fn()
    const field: TemplateField = { key: 'observacao', label: 'Observação', type: 'text', weight: 1 }
    render(<DynamicField field={field} value={undefined} onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Observação'), { target: { value: 'texto livre' } })

    expect(onChange).toHaveBeenCalledWith('texto livre')
  })
})
