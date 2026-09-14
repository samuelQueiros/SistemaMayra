import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import TemplateBuilder from './TemplateBuilder'
import type { TemplateSchemaJSON } from '../api/types'

const SCHEMA_INICIAL: TemplateSchemaJSON = {
  name: 'Escala De Teste',
  rule_type: 'sum_threshold',
  areas: [],
  classification_ranges: [],
  chart: { type: 'bar', group_by: 'areas' },
}

// Wrapper controlado, como o TemplateBuilder é usado de verdade em
// ModelosDeLaudo.tsx — permite inspecionar o estado atualizado via texto
// na tela (o próprio nome/label digitado), sem precisar mockar nada.
function ControlledBuilder() {
  const [value, setValue] = useState(SCHEMA_INICIAL)
  return <TemplateBuilder value={value} onChange={setValue} />
}

describe('TemplateBuilder', () => {
  it('adicionar uma área faz ela aparecer na tela', () => {
    render(<ControlledBuilder />)

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar Área' }))

    expect(screen.getByDisplayValue('Área 1')).toBeInTheDocument()
  })

  it('adicionar um campo dentro de uma área faz o editor do campo aparecer', () => {
    render(<ControlledBuilder />)

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar Área' }))
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar Campo' }))

    expect(screen.getByDisplayValue('Campo 1')).toBeInTheDocument()
  })

  it('trocar o tipo de regra para count_threshold mostra o campo de valores que contam', () => {
    render(<ControlledBuilder />)

    fireEvent.change(screen.getByLabelText('Tipo De Regra De Pontuação'), {
      target: { value: 'count_threshold' },
    })

    expect(screen.getByLabelText(/Valores Que Contam/)).toBeInTheDocument()
  })

  it('adicionar uma faixa de classificação faz ela aparecer na tela', () => {
    render(<ControlledBuilder />)

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar Faixa' }))

    expect(screen.getByDisplayValue('Nova Faixa')).toBeInTheDocument()
  })
})
