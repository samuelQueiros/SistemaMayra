import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from './client'
import { gerarLaudoPorIA } from './laudoIA'
import type { AndamentoDoLaudoIA } from './laudoIA'

vi.mock('./client', async (original) => ({ ...(await original<typeof client>()), enviarFormulario: vi.fn(), apiGet: vi.fn() }))

const andamento = (mudancas: Partial<AndamentoDoLaudoIA>): AndamentoDoLaudoIA => ({
  id: 'j1',
  status: 'processando',
  mensagem: '',
  documentos: [],
  report_id: null,
  erro: null,
  ...mudancas,
})

describe('gerarLaudoPorIA', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('começa a geração e acompanha o andamento até o laudo ficar pronto', async () => {
    vi.mocked(client.enviarFormulario).mockResolvedValue({ job_id: 'j1' })
    vi.mocked(client.apiGet)
      .mockResolvedValueOnce(andamento({ mensagem: 'Lendo documento 1 de 2…' }))
      .mockRejectedValueOnce(new client.ApiError(0, 'sem conexão')) // oscilação de rede: continua
      .mockRejectedValueOnce(new client.ApiError(502, 'proxy')) // erro passageiro do servidor: continua
      .mockResolvedValueOnce(andamento({ status: 'concluido', report_id: 'l9' }))
    const avisos: string[] = []

    const promessa = gerarLaudoPorIA('p1', [], '', { campos: [], contexto: '' }, (a) => avisos.push(a.mensagem), '2026-10-15', 'Gama – DF')
    await vi.runAllTimersAsync()

    await expect(promessa).resolves.toEqual({ id: 'l9' })
    const formulario = vi.mocked(client.enviarFormulario).mock.calls[0][1]
    expect(formulario.get('data_relatorio')).toBe('2026-10-15')
    expect(formulario.get('cidade')).toBe('Gama – DF')
    expect(client.apiGet).toHaveBeenCalledWith('/laudo-ia/jobs/j1')
    expect(avisos[0]).toBe('Lendo documento 1 de 2…')
  })

  it('repassa a mensagem de erro da geração', async () => {
    vi.mocked(client.enviarFormulario).mockResolvedValue({ job_id: 'j2' })
    vi.mocked(client.apiGet).mockResolvedValue(andamento({ status: 'erro', erro: "Não foi possível ler 'escola.pdf'." }))

    const promessa = gerarLaudoPorIA('p1', [], '', { campos: [], contexto: '' }, undefined, '2026-10-15', '')
    const verificacao = expect(promessa).rejects.toThrow("Não foi possível ler 'escola.pdf'.")
    await vi.runAllTimersAsync()
    await verificacao
  })
})
