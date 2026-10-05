import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getAISettings, updateAISettings } from '../api/aiSettings'
import type { AISettings } from '../api/aiSettings'
import { me as getMe, updateProfile } from '../api/auth'
import { Alert, Badge, Button, Card, Input, PageHeader, Select } from '../components/ds'
import { EditorCapa } from '../components/EditorCapa'
import { ModelosDeProtocolo } from '../components/ModelosDeProtocolo'

type Provider = 'anthropic' | 'openai' | 'google'

const MODELOS_SUGERIDOS: Record<Provider, string[]> = {
  anthropic: ['claude-sonnet-5', 'claude-opus-5', 'claude-haiku-4-5-20251001'],
  openai: ['gpt-5', 'gpt-5-mini'],
  google: ['gemini-3.6-flash', 'gemini-2.5-pro'],
}

const NOMES_PROVEDOR: Record<Provider, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI (GPT)',
  google: 'Google (Gemini)',
}

export default function Configuracoes() {
  const [current, setCurrent] = useState<AISettings | null>(null)
  const [loading, setLoading] = useState(true)

  const [provider, setProvider] = useState<Provider>('anthropic')
  const [model, setModel] = useState('claude-sonnet-5')
  const [apiKey, setApiKey] = useState('')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    getAISettings()
      .then((data) => {
        setCurrent(data)
        if (data.provider === 'anthropic' || data.provider === 'openai' || data.provider === 'google') {
          setProvider(data.provider)
        }
        setModel(data.model)
      })
      .catch(() => setError('Não foi possível carregar as configurações de IA.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await updateAISettings({ provider, model, api_key: apiKey })
      setCurrent(updated)
      setApiKey('')
      setSuccess(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível salvar a configuração.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p>Carregando...</p>

  return (
    <div>
      <PageHeader eyebrow="Preferências" title="Configurações" description="Registro profissional, capa dos relatórios, modelos de protocolo e integração com IA." />

      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        <RegistroProfissional />

        <EditorCapa />

        <ModelosDeProtocolo />

        <Card title="Configurações Da IA">
          <p style={{ color: 'var(--np-text-muted)', marginTop: 0 }}>
            Configure aqui a chave de acesso à IA usada para redigir o texto descritivo dos relatórios
            (ver SPEC.md seção 5). Sem isso configurado, o sistema continua gerando a pontuação e o
            gráfico normalmente — só o texto por IA não fica disponível.
          </p>

          {current && (
            <p>
              <strong>Situação atual:</strong>{' '}
              {current.api_key_configured ? (
                <Badge tone="success">
                  Configurado ({current.provider} / {current.model} — chave {current.api_key_preview})
                </Badge>
              ) : (
                <Badge tone="neutral">Ainda não configurado</Badge>
              )}
            </p>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
            <Select
              id="provider"
              label="Provedor De IA"
              value={provider}
              onChange={(e) => {
                const novo = e.target.value as Provider
                setProvider(novo)
                setModel(MODELOS_SUGERIDOS[novo][0])
              }}
              options={(Object.keys(NOMES_PROVEDOR) as Provider[]).map((p) => ({ value: p, label: NOMES_PROVEDOR[p] }))}
            />

            <Input
              id="model"
              label="Modelo"
              list="modelos-sugeridos"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
            />
            <datalist id="modelos-sugeridos">
              {MODELOS_SUGERIDOS[provider].map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>

            <Input
              id="api-key"
              label="Chave De API"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              required
              hint={current?.api_key_configured ? 'Já existe uma chave configurada. Para trocar de modelo/provedor sem trocar a chave, digite a mesma chave novamente.' : undefined}
            />

            {provider === 'google' && (
              <Alert tone="info">
                A assinatura do Google (Gemini Advanced / Google AI Pro) é separada da chave de API de
                desenvolvedor — gere a chave em{' '}
                <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
                  aistudio.google.com/app/apikey
                </a>{' '}
                (usa a cobrança do Google Cloud, não a mensalidade do app do Gemini).
              </Alert>
            )}

            {error && <Alert tone="danger">{error}</Alert>}
            {success && <Alert tone="success">Configuração salva com sucesso.</Alert>}

            <Button type="submit" disabled={saving || !apiKey} style={{ justifySelf: 'start' }}>
              {saving ? 'Salvando...' : 'Salvar Configuração'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}

function RegistroProfissional() {
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    getMe()
      .then((data) => setValue(data.professional_registration ?? ''))
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setSuccess(false)
    try {
      await updateProfile({ professional_registration: value || null })
      setSuccess(true)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return null

  return (
    <Card title="Registro Profissional" subtitle="Usado no bloco de assinatura do PDF completo (ex.: número do CRP).">
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <Input
          id="registro-profissional"
          label="Registro Profissional (Ex.: CRP)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="CRP 12/34567"
        />
        {success && <Alert tone="success">Registro salvo com sucesso.</Alert>}
        <Button type="submit" disabled={saving} style={{ justifySelf: 'start' }}>
          {saving ? 'Salvando...' : 'Salvar Registro'}
        </Button>
      </form>
    </Card>
  )
}
