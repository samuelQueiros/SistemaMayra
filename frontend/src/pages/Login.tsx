import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Button, Card, Input } from '../components/ds'
import styles from './Login.module.css'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [searchParams] = useSearchParams()
  const sessaoExpirada = searchParams.get('sessao') === 'expirada'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/pacientes')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível entrar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <Card style={{ width: '100%', maxWidth: 380 }}>
        <img src="/logo-neuropp.png" alt="Neuropp Mayra Vanessa" className={styles.logo} />
        <h1 className={styles.title}>Entrar</h1>
        <p className={styles.subtitle}>Sistema de Relatório Automático para Psicólogos</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          {!error && sessaoExpirada && (
            <Alert tone="warning">Sua sessão expirou por segurança. Entre novamente para continuar de onde parou.</Alert>
          )}
          {error && <Alert tone="danger">{error}</Alert>}

          <Input
            id="email"
            label="E-mail"
            type="email"
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Input
            id="password"
            label="Senha"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button type="submit" disabled={loading} fullWidth style={{ marginTop: 'var(--np-space-2)' }}>
            {loading ? 'Entrando...' : 'Entrar'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
