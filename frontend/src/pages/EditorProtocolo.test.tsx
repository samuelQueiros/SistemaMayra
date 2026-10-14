import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/protocolos'
import EditorProtocolo from './EditorProtocolo'

vi.mock('../api/protocolos', () => ({ createProtocolo: vi.fn(), getProtocolo: vi.fn(), updateProtocolo: vi.fn() }))
vi.mock('../api/auth', () => ({ me: vi.fn() }))

function renderizar() {
  return render(
    <MemoryRouter initialEntries={['/configuracoes/protocolos/novo']}>
      <Routes>
        <Route path="/configuracoes/protocolos/:id" element={<EditorProtocolo />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('EditorProtocolo', () => {
  beforeEach(() => {
    vi.mocked(api.createProtocolo).mockImplementation(async (m) => ({
      id: 'novo-id',
      name: m.name,
      version: 1,
      arquivado: false,
      created_at: '',
      schema_json: m,
    }))
  })

  it('não salva sem nome e explica o que falta', async () => {
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: 'Salvar modelo' }))
    expect(await screen.findByText('Dê um nome ao modelo.')).toBeInTheDocument()
    expect(api.createProtocolo).not.toHaveBeenCalled()
  })

  it('monta perguntas, escala com faixa e texto com variável, e salva no formato do backend', async () => {
    renderizar()
    fireEvent.change(screen.getByLabelText(/Nome do modelo/), { target: { value: 'Anamnese Infantil' } })
    fireEvent.change(screen.getByLabelText('Pergunta 1'), { target: { value: 'Queixa principal' } })

    // Variável da resposta da pergunta, inserida pelo botão
    fireEvent.click(screen.getByRole('button', { name: '+ Resposta: Queixa principal' }))

    fireEvent.click(screen.getByRole('button', { name: 'Escala pontuada' }))
    fireEvent.change(screen.getByLabelText('Item 1'), { target: { value: 'Distrai-se facilmente' } })
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar faixa' }))
    fireEvent.change(screen.getByLabelText('Classificação'), { target: { value: 'Leve' } })

    fireEvent.click(screen.getByRole('button', { name: 'Salvar modelo' }))
    await waitFor(() => expect(api.createProtocolo).toHaveBeenCalled())
    const modelo = vi.mocked(api.createProtocolo).mock.calls[0][0]

    expect(modelo.name).toBe('Anamnese Infantil')
    const [perguntas, escala] = modelo.secoes
    expect(perguntas.perguntas![0]).toMatchObject({ id: 'queixa_principal', rotulo: 'Queixa principal', tipo: 'texto_curto', opcoes: null })
    expect(perguntas.relatorio.texto_padrao).toBe('{q:queixa_principal}')
    expect(escala.tipo).toBe('escala')
    expect(escala.escala!.itens[0].rotulo).toBe('Distrai-se facilmente')
    expect(escala.escala!.faixas).toEqual([{ min: 0, max: 5, rotulo: 'Leve', texto_relatorio: '' }])
    expect(escala.perguntas).toBeNull()
  })
})
