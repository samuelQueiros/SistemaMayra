import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as auth from '../api/auth'
import { EditorCapa } from './EditorCapa'

vi.mock('../api/auth', () => ({
  me: vi.fn(),
  uploadCapa: vi.fn(),
  removeCapa: vi.fn(),
  updateCapaConfig: vi.fn(),
  fetchCapaUrl: vi.fn(),
}))

const perfil = {
  id: '1',
  name: 'Mayra',
  email: 'mayra@example.com',
  professional_registration: null,
}

function mockarPreview() {
  const preview = screen.getByTestId('preview-capa')
  preview.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 200, height: 400, right: 200, bottom: 400, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect
  return preview
}

describe('EditorCapa', () => {
  beforeEach(() => {
    vi.mocked(auth.me).mockResolvedValue({ ...perfil, tem_capa_personalizada: false, capa_config: null })
    vi.mocked(auth.updateCapaConfig).mockResolvedValue(perfil)
    vi.mocked(auth.uploadCapa).mockResolvedValue({ ...perfil, tem_capa_personalizada: true, capa_config: null })
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:capa')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('sem capa própria mostra a arte padrão com a área do nome', async () => {
    render(<EditorCapa />)

    expect(await screen.findByAltText('Prévia da capa do relatório')).toHaveAttribute('src', '/capa-relatorio.jpg')
    expect(screen.getByTestId('area-nome')).toBeInTheDocument()
    expect(screen.queryByText('Voltar à capa padrão')).not.toBeInTheDocument()
  })

  it('arrastar sobre a prévia marca a área do nome e salva em frações da capa', async () => {
    render(<EditorCapa />)
    await screen.findByAltText('Prévia da capa do relatório')
    const preview = mockarPreview()

    fireEvent.pointerDown(preview, { clientX: 20, clientY: 100, pointerId: 1 })
    fireEvent.pointerMove(preview, { clientX: 180, clientY: 120, pointerId: 1 })
    fireEvent.pointerUp(preview, { pointerId: 1 })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar capa' }))

    await waitFor(() => expect(auth.updateCapaConfig).toHaveBeenCalled())
    const config = vi.mocked(auth.updateCapaConfig).mock.calls[0][0]
    expect(config.escreverNome).toBe(true)
    expect(config.faixa.x).toBeCloseTo(0.1)
    expect(config.faixa.y).toBeCloseTo(0.25)
    expect(config.faixa.largura).toBeCloseTo(0.8)
    expect(config.faixa.altura).toBeCloseTo(0.05)
  })

  it('ao enviar uma capa nova, o nome começa desligado até ela marcar a área', async () => {
    render(<EditorCapa />)
    await screen.findByAltText('Prévia da capa do relatório')

    const arquivo = new File(['png'], 'capa.png', { type: 'image/png' })
    fireEvent.change(screen.getByTestId('arquivo-capa'), { target: { files: [arquivo] } })

    await waitFor(() => expect(auth.uploadCapa).toHaveBeenCalledWith(arquivo))
    expect(await screen.findByText('Voltar à capa padrão')).toBeInTheDocument()
    expect(screen.queryByTestId('area-nome')).not.toBeInTheDocument()
    expect(screen.getByAltText('Prévia da capa do relatório')).toHaveAttribute('src', 'blob:capa')
  })
})
