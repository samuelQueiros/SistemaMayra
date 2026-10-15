import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as anexos from '../../api/anexos'
import * as pendencias from '../../api/pendencias'
import { CompletarLaudo } from './CompletarLaudo'

vi.mock('../../api/anexos', async (original) => ({
  ...(await original<typeof anexos>()),
  enviarAnexo: vi.fn(),
  listarAnexos: vi.fn(),
  apagarAnexo: vi.fn(),
}))
vi.mock('../../api/pendencias', () => ({ getPendencias: vi.fn() }))

const GESTACAO = {
  essenciais: { total: 1, resolvidos: 0 },
  grupos: [
    {
      chave: 'gestacao',
      titulo: 'Gestação e parto',
      escala: false,
      essencial: true,
      pendentes: 1,
      itens: [{ chave: 'parto', rotulo: 'Parto', essencial: true, campos: [{ id: 'parto', tipo: 'texto' as const, opcoes: [], min: null, max: null }], valores: {}, situacao: null, origem: null, sugestoes: [] }],
    },
  ],
  escalas_para_adicionar: [],
}
const anexo = (status: anexos.Anexo['status'], sugestoes = 0): anexos.Anexo => ({
  id: 'a1', nome: 'ficha.jpg', mime: 'image/jpeg', secao: 'gestacao', status, erro: null, sugestoes, created_at: '2026-10-15T10:00:00Z',
})

describe('CompletarLaudo', () => {
  beforeEach(() => {
    vi.mocked(pendencias.getPendencias).mockResolvedValue(GESTACAO)
    vi.mocked(anexos.listarAnexos).mockResolvedValue([])
  })

  it('anexa uma foto na seção, mostra a leitura e recarrega as sugestões quando a IA termina', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(anexos.enviarAnexo).mockResolvedValue(anexo('analisando'))
    render(<CompletarLaudo laudoId="l1" pacienteId="p1" obterCatalogo={vi.fn()} />)

    const secao = await screen.findByRole('region', { name: 'Gestação e parto' })
    fireEvent.click(within(secao).getByRole('button', { name: 'Anexar' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Tirar foto' }))
    const foto = new File(['jpg'], 'ficha.jpg', { type: 'image/jpeg' })
    await act(async () => {
      fireEvent.change(screen.getByTestId('anexo-camera'), { target: { files: [foto] } })
    })
    expect(anexos.enviarAnexo).toHaveBeenCalledWith('p1', 'l1', foto, 'gestacao')
    expect(screen.getByTestId('anexo-camera')).toHaveAttribute('capture', 'environment') // câmera direto no celular
    expect(await screen.findByText('lendo…')).toBeInTheDocument()

    vi.mocked(anexos.listarAnexos).mockResolvedValue([anexo('pronto', 2)])
    const chamadasAntes = vi.mocked(pendencias.getPendencias).mock.calls.length
    await act(async () => vi.advanceTimersByTime(3100))
    expect(await screen.findByText('2 sugestões encontradas')).toBeInTheDocument()
    expect(vi.mocked(pendencias.getPendencias).mock.calls.length).toBeGreaterThan(chamadasAntes)
    vi.useRealTimers()
  })

  it('o anexo geral aceita foto e PDF', async () => {
    render(<CompletarLaudo laudoId="l1" pacienteId="p1" obterCatalogo={vi.fn()} />)
    expect(await screen.findByRole('button', { name: 'Anexar foto ou documento' })).toBeInTheDocument()
    expect(screen.getByTestId('anexo-arquivo')).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp,application/pdf')
  })
})
