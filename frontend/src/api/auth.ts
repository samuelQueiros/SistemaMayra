import { apiDelete, apiGet, apiPost, apiPostFile, apiPut, fetchObjectUrl } from './client'
import type { CapaConfig, Psychologist } from './types'

interface Token {
  access_token: string
  token_type: string
}

export const login = (email: string, password: string) =>
  apiPost<Token>('/auth/login', { email, password })

export const me = () => apiGet<Psychologist>('/auth/me')

export const updateProfile = (data: { professional_registration: string | null }) =>
  apiPut<Psychologist>('/auth/me', data)

export const uploadCapa = (file: File) => apiPostFile<Psychologist>('/auth/me/capa', file, 'PUT')

export const removeCapa = () => apiDelete<Psychologist>('/auth/me/capa')

export const updateCapaConfig = (config: CapaConfig) => apiPut<Psychologist>('/auth/me/capa/config', config)

export const fetchCapaUrl = () => fetchObjectUrl('/auth/me/capa/arquivo')
