import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/protocolos'
import NovoAtendimento from './NovoAtendimento'

vi.mock('../api/protocolos', () => ({ listProtocolos: vi.fn() }))

const modelo = {
  id: 'm1',
  name: 'Anamnese Infantil',
  version: 1,
  arquivado: false,
  created_at: '2026-10-05T00:00:00',
  schema_json: { rule_type: 'protocolo' as const, name: 'Anamnese Infantil', titulo_relatorio: 'R', secoes: [], descricao: 'Modelo curto' },
}

function renderizar(url = '/atendimento/novo') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <NovoAtendimento />
    </MemoryRouter>,
  )
}

describe('NovoAtendimento', () => {
  beforeEach(() => vi.mocked(api.listProtocolos).mockReset())

  it('sem modelos próprios abre direto o protocolo padrão', async () => {
    vi.mocked(api.listProtocolos).mockResolvedValue([])
    renderizar()
    expect(await screen.findByTitle('Formulário De Avaliação')).toHaveAttribute('src', '/formulario-novo-paciente.html')
  })

  it('com modelos próprios pergunta qual protocolo usar, levando o paciente junto', async () => {
    vi.mocked(api.listProtocolos).mockResolvedValue([modelo])
    renderizar('/atendimento/novo?paciente=p1')

    expect(await screen.findByText('Qual protocolo você vai usar neste atendimento?')).toBeInTheDocument()
    expect(screen.getByText('Anamnese Infantil').closest('a')).toHaveAttribute('href', '/atendimento/protocolo/m1?paciente=p1')
    expect(screen.getByText('Avaliação Neuropsicopedagógica E Análise Comportamental').closest('a')).toHaveAttribute(
      'href',
      '/atendimento/novo?protocolo=padrao&paciente=p1',
    )
    expect(screen.queryByTitle('Formulário De Avaliação')).not.toBeInTheDocument()
  })

  it('escolhido o padrão, abre o formulário de sempre sem consultar modelos', async () => {
    renderizar('/atendimento/novo?protocolo=padrao&paciente=p1')
    expect(await screen.findByTitle('Formulário De Avaliação')).toHaveAttribute('src', '/formulario-novo-paciente.html?paciente=p1')
    expect(api.listProtocolos).not.toHaveBeenCalled()
  })
})
