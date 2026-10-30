/** Tela de login. */
import { ArrowRight, Eye, EyeOff, Lock, Mail } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Button, IconButton, Input } from '../components/ds'
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
  const [mostrarSenha, setMostrarSenha] = useState(false)

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
      <section className={`card card-glass ${styles.card}`}>
        <img src="/identidade/logo.png" alt="Mayra Vanessa — Neuropsicopedagoga" className={styles.logo} />
        <h1 className={styles.title}>Entrar</h1>
        <p className={styles.subtitle}>Sistema de relatório automático para psicólogos</p>

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
            prefix={<Mail />}
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Input
            id="password"
            label="Senha"
            type={mostrarSenha ? 'text' : 'password'}
            placeholder="••••••••"
            prefix={<Lock />}
            autoComplete="current-password"
            suffix={
              <IconButton
                label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
                icon={mostrarSenha ? <EyeOff /> : <Eye />}
                onClick={() => setMostrarSenha((v) => !v)}
              />
            }
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button type="submit" size="lg" loading={loading} loadingLabel="Entrando…" fullWidth iconRight={<ArrowRight />} style={{ marginTop: 'var(--s-2)' }}>
            Entrar
          </Button>
        </form>
      </section>
    </div>
  )
}
