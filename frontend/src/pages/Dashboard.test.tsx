import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import * as reports from '../api/reports'
import Dashboard from './Dashboard'

vi.mock('../api/patients', () => ({
  listPatients: vi.fn().mockResolvedValue([
    { id: 'p1', name: 'Ana Souza', birth_date: '2018-03-15', notes: null, sex: null, school_info: null },
    { id: 'p2', name: 'João Conceição', birth_date: '2019-07-02', notes: null, sex: null, school_info: null },
  ]),
}))
vi.mock('../api/stats', () => ({ getStatsSummary: vi.fn().mockResolvedValue(null) }))
vi.mock('../api/templates', () => ({ listTemplates: vi.fn().mockResolvedValue([{ id: 't1', name: 'Avaliação', version: 1, schema_json: {} }]) }))
vi.mock('../api/reports', () => ({
  listReports: vi.fn().mockResolvedValue([
    { id: 'antigo', template_id: 't1', template_name_override: null, created_at: '2026-09-01T10:00:00' },
    { id: 'novo', template_id: 't1', template_name_override: 'Reavaliação', created_at: '2026-10-01T10:00:00' },
  ]),
  downloadReportPdf: vi.fn().mockResolvedValue(undefined),
  downloadReportDocx: vi.fn().mockResolvedValue(undefined),
}))

describe('Todos Os Pacientes', () => {
  it('cada paciente tem histórico, novo atendimento, formulário dos responsáveis e seções clínicas', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    const linha = (await screen.findByText('Ana Souza')).closest('tr')!
    expect(screen.queryByText('Protocolos Por Modelo')).not.toBeInTheDocument()
    const link = (nome: string) => within(linha).getByRole('link', { name: nome })
    expect(link('Histórico')).toHaveAttribute('href', '/pacientes/p1/historico')
    expect(link('Novo Atendimento')).toHaveAttribute('href', '/atendimento/novo?paciente=p1')
    expect(link('Formulário Dos Responsáveis')).toHaveAttribute('href', '/pacientes/p1/formularios-responsaveis')
    expect(link('Seções Clínicas')).toHaveAttribute('href', '/pacientes/p1/secoes-clinicas')
  })

  it('PDF / Word abre a escolha do relatório, mais recente primeiro, e baixa o escolhido', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    fireEvent.click((await screen.findAllByRole('button', { name: 'PDF / Word' }))[0])
    const dialogo = await screen.findByRole('dialog', { name: 'Baixar relatório de Ana Souza' })
    const itens = await within(dialogo).findAllByText(/Reavaliação|Avaliação/)
    expect(itens[0]).toHaveTextContent('Reavaliação')
    expect(within(dialogo).getByText('Mais recente')).toBeInTheDocument()

    fireEvent.click(within(dialogo).getAllByRole('button', { name: 'Word' })[0])
    expect(reports.downloadReportDocx).toHaveBeenCalledWith('novo', 'relatorio_Ana_Souza.docx')
    await vi.waitFor(() => expect(within(dialogo).getAllByRole('button', { name: 'PDF' })[1]).toBeEnabled())
    fireEvent.click(within(dialogo).getAllByRole('button', { name: 'PDF' })[1])
    expect(reports.downloadReportPdf).toHaveBeenCalledWith('antigo', 'relatorio_Ana_Souza.pdf')

    fireEvent.click(within(dialogo).getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('pesquisa de pacientes', () => {
  it('filtra por nome sem diferenciar acentos e por data de nascimento', async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    )
    await screen.findByText('Ana Souza')
    const busca = screen.getByPlaceholderText('Pesquisar por nome ou data de nascimento')

    fireEvent.change(busca, { target: { value: 'joao conceicao' } })
    expect(screen.getByText('João Conceição')).toBeInTheDocument()
    expect(screen.queryByText('Ana Souza')).not.toBeInTheDocument()
    expect(screen.getByText('1 de 2 pacientes')).toBeInTheDocument()

    fireEvent.change(busca, { target: { value: '15/03' } })
    expect(screen.getByText('Ana Souza')).toBeInTheDocument()
    expect(screen.queryByText('João Conceição')).not.toBeInTheDocument()

    fireEvent.change(busca, { target: { value: 'zzz' } })
    expect(screen.getByText('Nenhum paciente encontrado para "zzz".')).toBeInTheDocument()
  })
})
