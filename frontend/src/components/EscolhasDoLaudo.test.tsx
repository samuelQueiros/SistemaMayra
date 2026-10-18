import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EscolhasDoLaudo } from './EscolhasDoLaudo'

function Tela() {
  const [hipoteses, setHipoteses] = useState<string[]>([])
  const [encaminhamentos, setEncaminhamentos] = useState<string[]>([])
  return (
    <>
      <EscolhasDoLaudo hipoteses={hipoteses} encaminhamentos={encaminhamentos} onHipoteses={setHipoteses} onEncaminhamentos={setEncaminhamentos} />
      <output data-testid="escolhas">{JSON.stringify({ hipoteses, encaminhamentos })}</output>
    </>
  )
}

const escolhas = () => JSON.parse(screen.getByTestId('escolhas').textContent || '{}')

describe('EscolhasDoLaudo', () => {
  it('abre os subtipos ao marcar a hipótese e os desmarca junto com ela', () => {
    render(<Tela />)
    expect(screen.queryByRole('group', { name: /Subtipos de Transtorno do Espectro Autista/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/^Transtorno do Espectro Autista – TEA/))
    fireEvent.click(screen.getByLabelText(/6A02\.0/))
    fireEvent.click(screen.getByLabelText(/^Transtorno Opositor Desafiador – TOD/))
    fireEvent.click(screen.getByLabelText('Fonoaudiologia'))
    expect(escolhas()).toEqual({ hipoteses: ['hip_tea', 'hip_tea_6a02_0', 'hip_tod'], encaminhamentos: ['enc_fonoaudiologia'] })

    fireEvent.click(screen.getByLabelText(/^Transtorno do Espectro Autista – TEA/))
    expect(escolhas().hipoteses).toEqual(['hip_tod'])
    expect(screen.queryByRole('group', { name: /Subtipos de Transtorno do Espectro Autista/ })).not.toBeInTheDocument()
  })
})
