import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as anexos from '../../api/anexos'
import * as api from '../../api/pendencias'
import type { PendenciasDoLaudo as Pendencias } from '../../api/pendencias'
import { CamposQueFaltam } from './CamposQueFaltam'

vi.mock('../../api/pendencias', () => ({
  getPendencias: vi.fn(),
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
    vi.mocked(api.salvarDadosComplementares).mockClear()
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
    expect(api.getPendencias).toHaveBeenCalledTimes(3) // resumo, modal, resumo de novo
    vi.useRealTimers()
  })

  it('"Salvar e gerar o protocolo" salva, fecha e pede a geração', async () => {
    const onGerar = renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Preencher campos' }))
    const modal = await screen.findByRole('dialog')
    fireEvent.change(await within(modal).findByRole('textbox', { name: 'Parto' }), { target: { value: 'Normal' } })
    await act(async () => {
      fireEvent.click(within(modal).getByRole('button', { name: 'Salvar e gerar o protocolo' }))
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
