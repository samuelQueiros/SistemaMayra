import { Code, Sparkles, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createTemplate, importTemplateFromDocument, listTemplates } from '../api/templates'
import type { ReportTemplate, TemplateSchemaJSON } from '../api/types'
import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader } from '../components/ds'
import TemplateBuilder from '../components/TemplateBuilder'

const EXEMPLO_EM_BRANCO: TemplateSchemaJSON = {
  name: 'Nome Da Escala',
  rule_type: 'sum_threshold',
  areas: [
    {
      key: 'area_1',
      label: 'Nome Da Área',
      fields: [{ key: 'score', label: 'Pontuação', type: 'scale', min: 0, max: 4, weight: 1 }],
    },
  ],
  classification_ranges: [
    { label: 'Normal', min: 0, max: 10 },
    { label: 'Grave', min: 11, max: 20 },
  ],
  chart: { type: 'bar', group_by: 'areas' },
}

export default function ModelosDeLaudo() {
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)

  const [name, setName] = useState('')
  const [schema, setSchema] = useState<TemplateSchemaJSON | null>(null)
  const [mode, setMode] = useState<'visual' | 'json'>('visual')
  const [jsonText, setJsonText] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  function carregarTemplates() {
    setLoading(true)
    listTemplates()
      .then(setTemplates)
      .catch(() => setListError('Não foi possível carregar os modelos cadastrados.'))
      .finally(() => setLoading(false))
  }

  useEffect(carregarTemplates, [])

  function abrirModelo(novoSchema: TemplateSchemaJSON) {
    setName(novoSchema.name || 'Modelo Importado')
    setSchema(novoSchema)
    setJsonText(JSON.stringify(novoSchema, null, 2))
    setMode('visual')
    setJsonError(null)
    setSaveError(null)
    setSaveSuccess(false)
  }

  function abrirEdicaoEmBranco() {
    abrirModelo(EXEMPLO_EM_BRANCO)
    setValidationErrors([])
  }

  function alternarParaJson() {
    if (schema) setJsonText(JSON.stringify(schema, null, 2))
    setMode('json')
  }

  function alternarParaVisual() {
    try {
      const parsed = JSON.parse(jsonText) as TemplateSchemaJSON
      setSchema(parsed)
      setJsonError(null)
      setMode('visual')
    } catch {
      setJsonError('O texto não é um JSON válido — corrija antes de voltar ao modo visual.')
    }
  }

  async function handleImportar(event: FormEvent) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) return

    setImporting(true)
    setImportError(null)
    try {
      const resultado = await importTemplateFromDocument(file)
      abrirModelo(resultado.draft_schema_json)
      setValidationErrors(resultado.validation_errors)
    } catch (err) {
      setImportError(
        err instanceof ApiError
          ? err.message
          : 'Não foi possível importar o documento. Verifique a configuração de IA em "Configurações".',
      )
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleSalvar(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    try {
      let schemaParaSalvar = schema
      if (mode === 'json') {
        schemaParaSalvar = JSON.parse(jsonText)
      }
      if (!schemaParaSalvar) return
      const created = await createTemplate(name || schemaParaSalvar.name, schemaParaSalvar)
      setTemplates((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setSaveSuccess(true)
      setValidationErrors([])
    } catch (err) {
      if (err instanceof SyntaxError) {
        setSaveError('O texto do modelo não é um JSON válido. Revise a formatação antes de salvar.')
      } else if (err instanceof ApiError) {
        setSaveError(err.message)
      } else {
        setSaveError('Não foi possível salvar o modelo.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p>Carregando...</p>

  return (
    <div>
      <PageHeader
        eyebrow="Escalas"
        title="Modelos De Laudo"
        description='Cada modelo (CARS, ATA, SNAP-IV, Portage/IPO, ou uma escala nova) define os campos do formulário e como a pontuação é calculada. Suba o documento da escala para a IA extrair um rascunho, ou monte um modelo do zero pelo editor visual — revise sempre antes de salvar.'
      />

      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        {listError && <Alert tone="danger">{listError}</Alert>}

        <Card title="Modelos Cadastrados">
          {templates.length === 0 ? (
            <EmptyState title="Nenhum modelo cadastrado ainda" description="Importe um documento ou monte um modelo abaixo." />
          ) : (
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'grid', gap: 'var(--np-space-2)' }}>
              {templates.map((t) => (
                <li key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--np-space-3)' }}>
                  {t.name} <Badge tone="brand">{t.schema_json.rule_type}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Importar De Um Documento">
          <form onSubmit={handleImportar} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
            <label style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
              <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)' }}>Documento Da Escala (PDF, DOCX Ou TXT)</span>
              <input id="documento" type="file" accept=".pdf,.docx,.txt" ref={fileInputRef} required />
            </label>
            {importError && <Alert tone="danger">{importError}</Alert>}
            <Button type="submit" disabled={importing} icon={<Upload size={16} />} style={{ justifySelf: 'start' }}>
              {importing ? 'Lendo Documento Com IA...' : 'Importar Com IA'}
            </Button>
          </form>
        </Card>

        <Button type="button" variant="ghost" icon={<Sparkles size={16} />} onClick={abrirEdicaoEmBranco} style={{ justifySelf: 'start' }}>
          Ou Montar Um Modelo Do Zero
        </Button>

        {(schema || mode === 'json') && (
          <Card
            title="Revisar Antes De Salvar"
            action={
              <Button
                type="button"
                size="sm"
                variant="outline"
                icon={<Code size={14} />}
                onClick={mode === 'visual' ? alternarParaJson : alternarParaVisual}
              >
                {mode === 'visual' ? 'Modo Avançado (JSON)' : 'Voltar Ao Editor Visual'}
              </Button>
            }
          >
            <form onSubmit={handleSalvar} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
              {validationErrors.length > 0 && (
                <Alert tone="warning" title="A IA extraiu um rascunho, mas ele ainda precisa de ajustes:">
                  <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                    {validationErrors.map((erro, i) => (
                      <li key={i}>{erro}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              <Input id="template-name" label="Nome Do Modelo (Como Vai Aparecer Na Lista)" value={name} onChange={(e) => setName(e.target.value)} required />

              {mode === 'visual' && schema ? (
                <TemplateBuilder value={schema} onChange={setSchema} />
              ) : (
                <label style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
                  <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)' }}>Formato Do Modelo (JSON — Ver TEMPLATES_LAUDOS.md)</span>
                  <textarea
                    id="template-json"
                    value={jsonText}
                    onChange={(e) => setJsonText(e.target.value)}
                    rows={20}
                    required
                    style={{
                      padding: 'var(--np-space-3) var(--np-field-pad-x)',
                      background: 'var(--np-surface)',
                      border: '1px solid var(--np-border-strong)',
                      borderRadius: 'var(--np-radius-sm)',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      color: 'var(--np-text)',
                      resize: 'vertical',
                    }}
                  />
                  {jsonError && <Alert tone="danger">{jsonError}</Alert>}
                </label>
              )}

              {saveError && <Alert tone="danger">{saveError}</Alert>}
              {saveSuccess && <Alert tone="success">Modelo salvo com sucesso.</Alert>}
              <Button type="submit" disabled={saving} style={{ justifySelf: 'start' }}>
                {saving ? 'Salvando...' : 'Salvar Modelo'}
              </Button>
            </form>
          </Card>
        )}
      </div>
    </div>
  )
}
