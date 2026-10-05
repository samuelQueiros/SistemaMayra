import { apiGet, apiPut } from './client'

export interface AISettings {
  provider: string
  model: string
  api_key_configured: boolean
  api_key_preview: string | null
}

export interface AISettingsInput {
  provider: string
  model: string
  api_key: string
}

// Provedores aceitos (backend: app/services/ai/provedores.py). `leitura_pdf`
// diz como os PDFs do Relatório Por IA chegam ao modelo.
export interface ProvedorIA {
  id: string
  nome: string
  leitura_pdf: 'nativa' | 'imagens' | 'texto'
  modelos: string[]
  link_chave: string
  observacao: string | null
}

export const getAISettings = () => apiGet<AISettings>('/settings/ai')

export const listProvedoresIA = () => apiGet<ProvedorIA[]>('/settings/ai/provedores')

export const updateAISettings = (data: AISettingsInput) => apiPut<AISettings>('/settings/ai', data)
