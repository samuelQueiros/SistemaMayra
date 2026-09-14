import { apiGet, apiPut } from './client'

export interface AISettings {
  provider: string
  model: string
  api_key_configured: boolean
  api_key_preview: string | null
}

export interface AISettingsInput {
  provider: 'anthropic' | 'openai' | 'google'
  model: string
  api_key: string
}

export const getAISettings = () => apiGet<AISettings>('/settings/ai')

export const updateAISettings = (data: AISettingsInput) => apiPut<AISettings>('/settings/ai', data)
