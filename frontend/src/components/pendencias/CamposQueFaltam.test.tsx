import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as anexos from '../../api/anexos'
import * as api from '../../api/pendencias'
import type { PendenciasDoLaudo as Pendencias } from '../../api/pendencias'
import { CamposQueFaltam } from './CamposQueFaltam'

vi.mock('../../api/pendencias', () => ({
  getPendencias: vi.fn(),
  excluirMetodos: vi.fn(),
  enviarCatalogoDoLaudo: vi.fn(),
  marcarEscalasAplicadas: vi.fn(),
  salvarDadosComplementares: vi.fn().mockResolvedValue({ dados: {} }),
}))
vi.mock('../../api/anexos', async (original) => ({ ...(await original<typeof anexos>()), listarAnexos: vi.fn().mockResolvedValue([]) }))

const texto = (chave: string, rotulo: string, essencial = true) => ({
  chave, rotulo, essencial, campos: [{ id: chave, tipo: 'texto' as const, opcoes: [], min: null, max: null }], valores: {}, situacao: null, origem: null, sugestoes: [],
})

const PENDENCIAS: Pendencias = {
  essenciais: { total: 3, resolvidos: 0 },
  estudo_de_caso: { editado: false },
  escalas_para_adicionar: [],
  grupos: [
    { chave: 'gestacao', titulo: 'Gestação e parto', escala: false, essencial: true, pendentes: 2, itens: [texto('parto', 'Parto'), texto('idadeGestacional', 'Idade Gestacional')] },
    { chave: 'escala_ata', titulo: 'Pontuações da ATA', escala: true, essencial: true, pendentes: 22, itens: Array.from({ length: 22 }, (_, i) => texto(`ata_item_${i}`, `Item ${i + 1}`)) },
    { chave: 'observacoes', titulo: 'Observações clínicas', escala: false, essencial: false, pendentes: 1, itens: [texto('observacoesClinicas', 'Observações Clínicas Gerais', false)] },
  ],
}

function renderizar(onGerar = vi.fn()) {
  render(<CamposQueFaltam laudoId="l1" pacienteId="p1" obterCatalogo={vi.fn()} onGerar={onGerar} />)
  return onGerar
}

describe('CamposQueFaltam', () => {
  beforeEach(() => {
    vi.mocked(api.getPendencias).mockResolvedValue(PENDENCIAS)
    vi.mocked(api.salvarDadosComplementares).mockReset().mockResolvedValue({ dados: {} })
  })

  afterEach(() => vi.useRealTimers())

  it.each(['Salvar', 'Atualizar relatório'])('%s aguarda o autosave e as edições novas', async (acao) => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let primeiro!: (v: { dados: {} }) => void
    let segundo!: (v: { dados: {} }) => void
    vi.mocked(api.salvarDadosComplementares)
      .mockImplementationOnce(() => new Promise(resolve => { primeiro = resolve }))
      .mockImplementationOnce(() => new Promise(resolve => { segundo = resolve }))
    const onGerar = renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Preencher campos' }))
    const modal = await screen.findByRole('dialog')
    const campo = await within(modal).findByRole('textbox', { name: 'Parto' })
    fireEvent.change(campo, { target: { value: 'Normal' } })
    await act(async () => { vi.advanceTimersByTime(900) })
    fireEvent.change(campo, { target: { value: 'Cesáreo' } })
    await act(async () => { vi.advanceTimersByTime(900) })
    expect(api.salvarDadosComplementares).toHaveBeenCalledTimes(1)
    await act(async () => { fireEvent.click(within(modal).getByRole('button', { name: acao })) })
    expect(onGerar).not.toHaveBeenCalled()
    expect(modal).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })
    fireEvent.click(modal)
    await act(async () => { primeiro({ dados: {} }) })
    expect(api.salvarDadosComplementares).toHaveBeenLastCalledWith('p1', { parto: { valor: 'Cesáreo', situacao: 'preenchido', origem: 'digitado' } })
    expect(onGerar).not.toHaveBeenCalled()
    expect(modal).toBeInTheDocument()
    await act(async () => { segundo({ dados: {} }) })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(onGerar).toHaveBeenCalledTimes(acao === 'Salvar' ? 0 : 1)
  })

  it('mantém os dados após falha no autosave e permite tentar novamente', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let falhar!: (e: Error) => void
    vi.mocked(api.salvarDadosComplementares).mockImplementationOnce(() => new Promise((_, reject) => { falhar = reject }))
    const onGerar = renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Preencher campos' }))
    const modal = await screen.findByRole('dialog')
    const campo = await within(modal).findByRole('textbox', { name: 'Parto' })
    fireEvent.change(campo, { target: { value: 'Normal' } })
    await act(async () => { vi.advanceTimersByTime(900) })
    fireEvent.change(campo, { target: { value: 'Cesáreo' } })
    fireEvent.click(within(modal).getByRole('button', { name: 'Atualizar relatório' }))
    await act(async () => { falhar(new Error('Sem conexão')) })
    expect(onGerar).not.toHaveBeenCalled()
    expect(modal).toBeInTheDocument()
    expect(campo).toHaveValue('Cesáreo')
    expect(screen.getByText('Não foi possível salvar. Verifique a conexão e tente de novo.')).toBeInTheDocument()
    await act(async () => { fireEvent.click(within(modal).getByRole('button', { name: 'Atualizar relatório' })) })
    expect(api.salvarDadosComplementares).toHaveBeenLastCalledWith('p1', { parto: { valor: 'Cesáreo', situacao: 'preenchido', origem: 'digitado' } })
    expect(onGerar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('mostra tudo o que falta, sem ids técnicos, nas cores do sistema', async () => {
    renderizar()
    expect(await screen.findByText('Há alguns campos que podem ser preenchidos:')).toBeInTheDocument()
    const resumo = screen.getByRole('region', { name: 'Campos que podem ser preenchidos' })
    expect(within(resumo).getByText('Gestação e parto')).toBeInTheDocument()
    expect(within(resumo).getByText('Parto · Idade gestacional')).toBeInTheDocument()
    expect(within(resumo).getByText('22 itens sem resposta')).toBeInTheDocument()
    expect(within(resumo).getByText('Observações clínicas')).toBeInTheDocument() // opcionais também aparecem
    expect(within(resumo).getByText('0 de 3 essenciais preenchidos')).toBeInTheDocument()
    expect(resumo.textContent).not.toMatch(/ata_item|observacoesClinicas/)
  })

  it('clicar numa seção abre o modal com os campos; Salvar grava e fecha', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderizar()
    fireEvent.click(await screen.findByRole('button', { name: /Gestação e parto/ }))
    const modal = await screen.findByRole('dialog', { name: 'Campos que faltam no laudo' })
    const parto = await within(modal).findByRole('textbox', { name: 'Parto' })
    fireEvent.change(parto, { target: { value: 'Cesáreo' } })
    await act(async () => {
      fireEvent.click(within(modal).getByRole('button', { name: 'Salvar' }))
    })
    expect(api.salvarDadosComplementares).toHaveBeenCalledWith('p1', { parto: { valor: 'Cesáreo', situacao: 'preenchido', origem: 'digitado' } })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.getPendencias).toHaveBeenCalledTimes(2) // resumo reutilizado no modal; recarga ao fechar
    vi.useRealTimers()
  })

  it('"Atualizar relatório" salva, fecha e pede a geração', async () => {
    const onGerar = renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Preencher campos' }))
    const modal = await screen.findByRole('dialog')
    fireEvent.change(await within(modal).findByRole('textbox', { name: 'Parto' }), { target: { value: 'Normal' } })
    await act(async () => {
      fireEvent.click(within(modal).getByRole('button', { name: 'Atualizar relatório' }))
    })
    expect(api.salvarDadosComplementares).toHaveBeenCalledTimes(1)
    expect(onGerar).toHaveBeenCalledWith(false)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('sem pendências, avisa que está tudo preenchido', async () => {
    vi.mocked(api.getPendencias).mockResolvedValue({ ...PENDENCIAS, grupos: [] })
    renderizar()
    expect(await screen.findByText('Todos os campos do protocolo estão preenchidos.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Preencher campos' })).not.toBeInTheDocument()
  })

  it('no resumo, cada item aparece uma vez só pelo nome principal', async () => {
    vi.mocked(api.getPendencias).mockResolvedValue({
      ...PENDENCIAS,
      grupos: [{ chave: 'funcoes_executivas', titulo: 'Funções executivas', escala: false, essencial: false, pendentes: 2,
        itens: [texto('fe_manif_0', 'Metacognição — Manifestação Observada', false), texto('fe_perc_0', 'Metacognição — Indicador (%)', false), texto('fe_manif_1', 'Planejamento — Manifestação Observada', false)] }],
    })
    renderizar()
    expect(await screen.findByText('Metacognição · Planejamento')).toBeInTheDocument()
  })
})


it('permite revisar e remover métodos mesmo com todos os campos preenchidos', async () => {
  vi.mocked(api.getPendencias).mockResolvedValue({ ...PENDENCIAS, grupos: [], metodos: [{ chave: 'cars', titulo: 'CARS', incluido: true }] })
  vi.mocked(api.excluirMetodos).mockResolvedValue({ ...PENDENCIAS, grupos: [], metodos: [{ chave: 'cars', titulo: 'CARS', incluido: false }] })
  renderizar()
  fireEvent.click(await screen.findByRole('button', { name: 'Revisar métodos' }))
  const cars = await screen.findByRole('checkbox', { name: 'CARS' })
  expect(cars).toBeChecked()
  await act(async () => { fireEvent.click(cars) })
  expect(api.excluirMetodos).toHaveBeenCalledWith('l1', ['cars'])
  expect(screen.getByRole('checkbox', { name: 'CARS' })).not.toBeChecked()
})
