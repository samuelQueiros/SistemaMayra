/** Estado de login da aplicação: psicóloga atual, entrar e sair. */
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import * as authApi from '../api/auth'
import { ApiError, clearToken, getToken, setToken } from '../api/client'
import type { Psychologist } from '../api/types'

interface AuthContextValue {
  psychologist: Psychologist | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [psychologist, setPsychologist] = useState<Psychologist | null>(null)
  const [hasToken, setHasToken] = useState<boolean>(() => Boolean(getToken()))

  useEffect(() => {
    if (!hasToken || psychologist) return
    authApi
      .me()
      .then(setPsychologist)
      .catch((err) => {
        // token salvo no navegador expirou ou é inválido — desloga
        if (err instanceof ApiError && err.status === 401) {
          clearToken()
          setHasToken(false)
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasToken])

  async function login(email: string, password: string) {
    const token = await authApi.login(email, password)
    setToken(token.access_token)
    setHasToken(true)
    const current = await authApi.me()
    setPsychologist(current)
  }

  function logout() {
    clearToken()
    setHasToken(false)
    setPsychologist(null)
  }

  return (
    <AuthContext.Provider value={{ psychologist, isAuthenticated: hasToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth precisa ser usado dentro de um AuthProvider')
  }
  return context
}
