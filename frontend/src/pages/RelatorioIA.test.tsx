import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import RelatorioIA from './RelatorioIA'

function Destino() {
  const location = useLocation()
  return <p>{location.pathname}{location.search}</p>
}

describe('Endereço antigo de Relatório Por IA', () => {
  it.each(['', '?paciente=p9'])('redireciona ao Relatório por IA preservando %s', async (search) => {
    render(
      <MemoryRouter initialEntries={[`/relatorio-ia${search}`]}>
        <Routes>
          <Route path="/relatorio-ia" element={<RelatorioIA />} />
          <Route path="/laudo-ia" element={<Destino />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByText(`/laudo-ia${search}`)).toBeInTheDocument()
  })
})
