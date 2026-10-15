import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../../api/pendencias'
import type { PendenciasDoLaudo as Pendencias } from '../../api/pendencias'
import { PendenciasDoLaudo } from './PendenciasDoLaudo'

vi.mock('../../api/pendencias', () => ({
  getPendencias: vi.fn(),
  enviarCatalogoDoLaudo: vi.fn(),
  marcarEscalasAplicadas: vi.fn(),
  salvarDadosComplementares: vi.fn().mockResolvedValue({ dados: {} }),
}))

const item = (chave: string, rotulo: string, tipo: 'opcao' | 'simnao' | 'texto', essencial = true) => ({
  chave,
  rotulo,
  essencial,
  campos: [{ id: chave, tipo, opcoes: tipo === 'opcao' ? [{ valor: 'Cesáreo', rotulo: 'Cesáreo' }, { valor: 'Normal', rotulo: 'Normal' }] : [], min: null, max: null }],
  valores: {},
  situacao: null,
  origem: null,
  sugestoes: [],
})

const PENDENCIAS: Pendencias = {
  essenciais: { total: 3, resolvidos: 0 },
  grupos: [
    { chave: 'gestacao', titulo: 'Gestação e parto', escala: false, essencial: true, pendentes: 2, itens: [item('parto', 'Parto', 'opcao'), item('sofrimentoFetal', 'História De Sofrimento Fetal', 'simnao')] },
    {
      chave: 'escala_ata',
      titulo: 'Pontuações da ATA',
      escala: true,
      essencial: true,
      pendentes: 22,
      itens: Array.from({ length: 22 }, (_, i) => item(`ata_item_${i}`, `Item ${i + 1} da ATA`, 'opcao')),
    },
    { chave: 'observacoes', titulo: 'Observações clínicas', escala: false, essencial: false, pendentes: 1, itens: [item('observacoesClinicas', 'Observações Clínicas Gerais', 'texto', false)] },
  ],
  escalas_para_adicionar: [{ chave: 'tod', titulo: 'TOD' }],
}

function renderizar() {
  return render(<PendenciasDoLaudo laudoId="l1" pacienteId="p1" obterCatalogo={vi.fn()} />)
}

describe('PendenciasDoLaudo', () => {
  beforeEach(() => {
    vi.mocked(api.getPendencias).mockResolvedValue(PENDENCIAS)
    vi.mocked(api.salvarDadosComplementares).mockClear()
  })

  it('mostra seções amigáveis, essenciais primeiro, escala agrupada e opcionais recolhidos', async () => {
    renderizar()
    expect(await screen.findByText('0 de 3 essenciais preenchidos')).toBeInTheDocument()
    expect(screen.getByText('Gestação e parto')).toBeInTheDocument()
    expect(screen.getByText('História de sofrimento fetal')).toBeInTheDocument() // primeira maiúscula
    expect(screen.getByText('22 itens sem resposta')).toBeInTheDocument()
    expect(screen.queryByText('Item 1 da ATA')).not.toBeInTheDocument() // escala fechada
    expect(screen.queryByText('Observações clínicas gerais')).not.toBeInTheDocument() // opcional recolhido
    expect(screen.queryByText(/ata_item/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Preencher' }))
    expect(screen.getByText('Item 1 da ATA')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Opcionais (1)' }))
    expect(screen.getByText('Observações clínicas gerais')).toBeInTheDocument()
  })

  it('salva sozinho depois de preencher e atualiza o progresso', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderizar()
    const parto = await screen.findByRole('combobox', { name: 'Parto' })
    fireEvent.change(parto, { target: { value: 'Cesáreo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sim' }))
    expect(screen.getByText('2 de 3 essenciais preenchidos')).toBeInTheDocument()
    expect(api.salvarDadosComplementares).not.toHaveBeenCalled()

    await act(async () => vi.advanceTimersByTime(900))
    expect(api.salvarDadosComplementares).toHaveBeenCalledTimes(1) // as duas mudanças num envio só
    expect(api.salvarDadosComplementares).toHaveBeenCalledWith('p1', {
      parto: { valor: 'Cesáreo', situacao: 'preenchido', origem: 'digitado' },
      sofrimentoFetal: { valor: 'Sim', situacao: 'preenchido', origem: 'digitado' },
    })
    expect(await screen.findByText(/Salvo às/)).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('dispensa um item com "Não informado pela família" e permite desfazer', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Mais opções para Parto' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Não informado pela família' }))
    const secao = screen.getByRole('region', { name: 'Gestação e parto' })
    expect(within(secao).getByText('Não informado pela família')).toBeInTheDocument()
    expect(screen.getByText('1 de 3 essenciais preenchidos')).toBeInTheDocument()
    await act(async () => vi.advanceTimersByTime(900))
    expect(api.salvarDadosComplementares).toHaveBeenLastCalledWith('p1', { parto: { situacao: 'nao_informado', valor: null } })

    fireEvent.click(within(secao).getByRole('button', { name: 'Desfazer' }))
    await act(async () => vi.advanceTimersByTime(900))
    expect(api.salvarDadosComplementares).toHaveBeenLastCalledWith('p1', { parto: null })
    vi.useRealTimers()
  })

  it('"Também apliquei" inclui a escala nas pendências', async () => {
    vi.mocked(api.marcarEscalasAplicadas).mockResolvedValue({ ...PENDENCIAS, escalas_para_adicionar: [] })
    renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'TOD' }))
    expect(api.marcarEscalasAplicadas).toHaveBeenCalledWith('l1', ['ata', 'tod'])
  })

  it('laudo antigo sem catálogo: lê no formulário e envia', async () => {
    const { ApiError } = await import('../../api/client')
    vi.mocked(api.getPendencias).mockRejectedValue(new ApiError(409, 'sem catálogo'))
    vi.mocked(api.enviarCatalogoDoLaudo).mockResolvedValue(PENDENCIAS)
    const catalogo = { campos: [], contexto: '' }
    render(<PendenciasDoLaudo laudoId="l1" pacienteId="p1" obterCatalogo={() => Promise.resolve(catalogo)} />)
    expect(await screen.findByText('Gestação e parto')).toBeInTheDocument()
    expect(api.enviarCatalogoDoLaudo).toHaveBeenCalledWith('l1', catalogo)
  })
})
