import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import * as api from '../api/relatoriosPdf'
import { EnvioDePdfsParaIA } from './EnvioDePdfsParaIA'

vi.mock('../api/relatoriosPdf', async (original) => ({
  ...(await original<typeof import('../api/relatoriosPdf')>()),
  gerarRelatorioPorPdfs: vi.fn(),
}))

const pdf = (nome: string) => new File(['%PDF-1.4'], nome, { type: 'application/pdf' })

function renderizar() {
  render(
    <MemoryRouter initialEntries={['/pacientes/p1/historico']}>
      <Routes>
        <Route path="/pacientes/p1/historico" element={<EnvioDePdfsParaIA patientId="p1" />} />
        <Route path="/pacientes/p1/relatorio-ia/:laudo" element={<p>Tela de revisão</p>} />
      </Routes>
    </MemoryRouter>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Relatório por IA (PDFs)' }))
}

const anexar = (arquivos: File[]) => fireEvent.change(screen.getByTestId('arquivos-pdf'), { target: { files: arquivos } })

describe('EnvioDePdfsParaIA', () => {
  beforeEach(() => {
    vi.mocked(api.gerarRelatorioPorPdfs).mockReset()
  })

  it('envia os PDFs com as observações e abre a tela de revisão', async () => {
    vi.mocked(api.gerarRelatorioPorPdfs).mockResolvedValue({ id: 'l1' } as api.LaudoRelatorioIA)
    renderizar()
    anexar([pdf('mae.pdf'), pdf('escola.pdf')])
    expect(screen.getByText('mae.pdf')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Observações para a IA (opcional)'), { target: { value: 'foco em atenção' } })
    fireEvent.click(screen.getByRole('button', { name: 'Gerar relatório' }))

    expect(await screen.findByText('Tela de revisão')).toBeInTheDocument()
    const [paciente, arquivos, obs] = vi.mocked(api.gerarRelatorioPorPdfs).mock.calls[0]
    expect(paciente).toBe('p1')
    expect(arquivos.map((a) => a.name)).toEqual(['mae.pdf', 'escola.pdf'])
    expect(obs).toBe('foco em atenção')
  })

  it('não aceita mais de 6 PDFs', () => {
    renderizar()
    anexar(Array.from({ length: 7 }, (_, i) => pdf(`${i}.pdf`)))
    expect(screen.getByText('Anexe no máximo 6 PDFs por relatório.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Gerar relatório' })).toBeDisabled()
  })

  it('recusa arquivo que não é PDF', () => {
    renderizar()
    anexar([new File(['x'], 'foto.png', { type: 'image/png' })])
    expect(screen.getByText(/"foto.png" não é um PDF/)).toBeInTheDocument()
  })

  it('mostra o erro da IA sem sair da tela', async () => {
    vi.mocked(api.gerarRelatorioPorPdfs).mockRejectedValue(new ApiError(502, 'O modelo precisa aceitar PDFs.'))
    renderizar()
    anexar([pdf('a.pdf')])
    fireEvent.click(screen.getByRole('button', { name: 'Gerar relatório' }))
    expect(await screen.findByText('O modelo precisa aceitar PDFs.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Gerar relatório' })).toBeEnabled()
  })
})
