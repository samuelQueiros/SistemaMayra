import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getAISettings, listProvedoresIA, updateAISettings } from '../api/aiSettings'
import type { AISettings, ProvedorIA } from '../api/aiSettings'
import { Alert, Badge, Button, Card, Input, PageHeader, Select } from '../components/ds'

const LEITURA_PDF: Record<ProvedorIA['leitura_pdf'], { tom: 'success' | 'warning' | 'danger'; texto: string }> = {
  nativa: { tom: 'success', texto: 'Lê os PDFs dos formulários por inteiro' },
  imagens: { tom: 'warning', texto: 'Lê os PDFs como imagens das páginas' },
  texto: { tom: 'danger', texto: 'Lê só o texto dos PDFs (pode perder a opção marcada)' },
}

export default function ConfiguracoesIA() {
  const [current, setCurrent] = useState<AISettings | null>(null)
  const [provedores, setProvedores] = useState<ProvedorIA[]>([])
  const [loading, setLoading] = useState(true)

  const [provider, setProvider] = useState('anthropic')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    Promise.all([getAISettings(), listProvedoresIA()])
      .then(([data, lista]) => {
        setCurrent(data)
        setProvedores(lista)
        const conhecido = lista.find((p) => p.id === data.provider) ?? lista[0]
        setProvider(conhecido?.id ?? 'anthropic')
        setModel(lista.some((p) => p.id === data.provider) ? data.model : (conhecido?.modelos[0] ?? ''))
      })
      .catch(() => setError('Não foi possível carregar as configurações de IA.'))
      .finally(() => setLoading(false))
  }, [])

  const info = provedores.find((p) => p.id === provider)
  const nomeDoProvedor = (id: string) => provedores.find((p) => p.id === id)?.nome ?? id

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
      <PageHeader eyebrow="Configurações" title="Inteligência Artificial" description="Configure o provedor, o modelo e a chave de acesso para a redação assistida dos relatórios." />

      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        <Card title="Configurações Da IA">
          <p style={{ color: 'var(--np-text-muted)', marginTop: 0 }}>
            Escolha a empresa de IA, o modelo e cole a chave de API dela. A IA é usada no Relatório Por IA a partir de formulários, nas considerações finais do protocolo
            e na importação de modelos.
          </p>

          {current && (
            <p>
              <strong>Situação atual:</strong>{' '}
              {current.api_key_configured ? (
                <Badge tone="success">
                  Configurado ({nomeDoProvedor(current.provider)} / {current.model} — chave {current.api_key_preview})
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
                const novo = provedores.find((p) => p.id === e.target.value)
                setProvider(e.target.value)
                setModel(novo?.modelos[0] ?? '')
              }}
              options={provedores.map((p) => ({ value: p.id, label: p.nome }))}
            />

            {info && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)', alignItems: 'center' }}>
                <Badge tone={LEITURA_PDF[info.leitura_pdf].tom}>{LEITURA_PDF[info.leitura_pdf].texto}</Badge>
                <a href={info.link_chave} target="_blank" rel="noreferrer" style={{ font: 'var(--np-type-caption)' }}>
                  Onde gerar a chave de API
                </a>
              </div>
            )}

            <Input
              id="model"
              label="Modelo"
              list="modelos-sugeridos"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
              hint="Escolha uma sugestão ou digite o nome exato de outro modelo da mesma empresa."
            />
            <datalist id="modelos-sugeridos">
              {(info?.modelos ?? []).map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>

            <Input
              id="api-key"
              label="Chave De API"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Cole aqui a chave de API"
              required
              hint={current?.api_key_configured ? 'Já existe uma chave configurada. Para trocar de modelo/provedor sem trocar a chave, digite a mesma chave novamente.' : undefined}
            />

            {info?.observacao && <Alert tone={info.leitura_pdf === 'texto' ? 'warning' : 'info'}>{info.observacao}</Alert>}

            {error && <Alert tone="danger">{error}</Alert>}
            {success && <Alert tone="success">Configuração salva com sucesso.</Alert>}

            <Button type="submit" disabled={saving || !apiKey || !model} style={{ justifySelf: 'start' }}>
              {saving ? 'Salvando...' : 'Salvar Configuração'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}
