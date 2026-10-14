import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from '../api/aiSettings'
import ConfiguracoesIA from './ConfiguracoesIA'

vi.mock('../api/aiSettings', () => ({
  getAISettings: vi.fn().mockResolvedValue({ provider: 'google', model: 'gemini-3.6-flash', api_key_configured: true, api_key_preview: '******abcd' }),
  listProvedoresIA: vi.fn().mockResolvedValue([
    { id: 'google', nome: 'Google (Gemini)', leitura_pdf: 'nativa', modelos: ['gemini-3.6-flash'], link_chave: 'https://aistudio.google.com/app/apikey', observacao: null },
    { id: 'xai', nome: 'xAI (Grok)', leitura_pdf: 'imagens', modelos: ['grok-4', 'grok-4-fast'], link_chave: 'https://console.x.ai', observacao: null },
    { id: 'deepseek', nome: 'DeepSeek', leitura_pdf: 'texto', modelos: ['deepseek-chat'], link_chave: 'https://platform.deepseek.com/api_keys', observacao: 'O DeepSeek não lê imagens.' },
  ]),
  updateAISettings: vi.fn().mockResolvedValue({ provider: 'xai', model: 'grok-4', api_key_configured: true, api_key_preview: '******9999' }),
}))

describe('Configurações → Inteligência Artificial', () => {
  it('lista os provedores do backend, mostra como cada um lê os PDFs e salva a escolha', async () => {
    render(<ConfiguracoesIA />)
    expect(await screen.findByText(/Configurado \(Google \(Gemini\) \/ gemini-3.6-flash/)).toBeInTheDocument()
    expect(screen.getByText('Lê os PDFs dos formulários por inteiro')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Provedor de IA'), { target: { value: 'deepseek' } })
    expect(screen.getByText('Lê só o texto dos PDFs (pode perder a opção marcada)')).toBeInTheDocument()
    expect(screen.getByText('O DeepSeek não lê imagens.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Modelo/)).toHaveValue('deepseek-chat')

    fireEvent.change(screen.getByLabelText('Provedor de IA'), { target: { value: 'xai' } })
    expect(screen.getByRole('link', { name: 'Onde gerar a chave de API' })).toHaveAttribute('href', 'https://console.x.ai')
    fireEvent.change(screen.getByLabelText(/Chave de API/), { target: { value: 'xai-9999' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar configuração' }))
    await waitFor(() => expect(api.updateAISettings).toHaveBeenCalledWith({ provider: 'xai', model: 'grok-4', api_key: 'xai-9999' }))
    expect(await screen.findByText('Configuração salva com sucesso.')).toBeInTheDocument()
  })
})
