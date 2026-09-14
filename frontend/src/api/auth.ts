import { apiGet, apiPost, apiPut } from './client'
import type { Psychologist } from './types'

interface Token {
  access_token: string
  token_type: string
}

export const login = (email: string, password: string) =>
  apiPost<Token>('/auth/login', { email, password })

export const me = () => apiGet<Psychologist>('/auth/me')

export const updateProfile = (data: { professional_registration: string | null }) =>
  apiPut<Psychologist>('/auth/me', data)
