import { Download, FileText, Loader2, Plus, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import DynamicField from '../components/DynamicField'
import ScoreChart from '../components/ScoreChart'
import { ApiError } from '../api/client'
import { createPatient, listPatients } from '../api/patients'
import { createReport, downloadReportPdf, generateReportText, updateReportText } from '../api/reports'
import { listTemplates } from '../api/templates'
import type { Answers, ComputedResult, Patient, Report, ReportTemplate, TemplateSchemaJSON } from '../api/types'
import { Alert, Badge, Button, Card, Input, PageHeader, ProgressBar, Select } from '../components/ds'

// Conta quantas perguntas do modelo já foram respondidas, para mostrar uma
// barra de progresso — facilita a orientação em formulários longos (ex.:
// CARS tem 15 áreas).
function contarProgresso(schema: TemplateSchemaJSON, answers: Answers): { respondidas: number; total: number } {
  let respondidas = 0
  let total = 0
  for (const area of schema.areas) {
    if (area.fields) {
      for (const field of area.fields) {
        total += 1
        const areaAnswers = answers[area.key] as Record<string, unknown> | undefined
        if (areaAnswers?.[field.key] !== undefined) respondidas += 1
      }
    }
    if (area.age_brackets) {
      for (const bracket of area.age_brackets) {
        for (const field of bracket.fields) {
          total += 1
          const bracketAnswers = (answers[area.key] as Record<string, Record<string, unknown>> | undefined)?.[bracket.label]
          if (bracketAnswers?.[field.key] !== undefined) respondidas += 1
        }
      }
    }
  }
  return { respondidas, total }
}

export default function NovoAtendimento() {
  const [searchParams] = useSearchParams()
  const [patients, setPatients] = useState<Patient[]>([])
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [loading, setLoading] = useState(true)

  const [patientId, setPatientId] = useState(searchParams.get('paciente') ?? '')
  const [templateId, setTemplateId] = useState('')
  const [answers, setAnswers] = useState<Answers>({})

  const [showNewPatientForm, setShowNewPatientForm] = useState(false)
  const [newPatientName, setNewPatientName] = useState('')
  const [newPatientBirth, setNewPatientBirth] = useState('')
  const [creatingPatient, setCreatingPatient] = useState(false)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<Report | null>(null)

  useEffect(() => {
    Promise.all([listPatients(), listTemplates()])
      .then(([p, t]) => {
        setPatients(p)
        setTemplates(t)
      })
      .catch(() => setError('Não foi possível carregar pacientes/modelos.'))
      .finally(() => setLoading(false))
  }, [])

  const template = templates.find((t) => t.id === templateId)
  const selectedPatient = patients.find((p) => p.id === patientId)

  function setFieldValue(areaKey: string, fieldKey: string, value: string | number | boolean | undefined) {
    setAnswers((prev) => {
      const next = { ...prev, [areaKey]: { ...prev[areaKey] } } as Answers
      const areaAnswers = next[areaKey] as Record<string, string | number | boolean>
      if (value === undefined) {
        delete areaAnswers[fieldKey]
      } else {
        areaAnswers[fieldKey] = value
      }
      return next
    })
  }

  // Áreas no formato "age_equivalent_percentage" (Portage) guardam as
  // respostas com um nível a mais: área -> faixa etária -> campo.
  function setBracketFieldValue(
    areaKey: string,
    bracketLabel: string,
    fieldKey: string,
    value: string | undefined,
  ) {
    setAnswers((prev) => {
      const prevArea = (prev[areaKey] ?? {}) as Record<string, Record<string, string>>
      const prevBracket = prevArea[bracketLabel] ?? {}
      const nextBracket = { ...prevBracket }
      if (value === undefined) {
        delete nextBracket[fieldKey]
      } else {
        nextBracket[fieldKey] = value
      }
      return { ...prev, [areaKey]: { ...prevArea, [bracketLabel]: nextBracket } }
    })
  }

  function handleTemplateChange(id: string) {
    setTemplateId(id)
    setAnswers({})
    setReport(null)
    setError(null)
  }

  async function handleCreatePatient(event: FormEvent) {
    event.preventDefault()
    setCreatingPatient(true)
    setError(null)
    try {
      const created = await createPatient({ name: newPatientName, birth_date: newPatientBirth })
      setPatients((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setPatientId(created.id)
      setShowNewPatientForm(false)
      setNewPatientName('')
      setNewPatientBirth('')
    } catch {
      setError('Não foi possível cadastrar o paciente.')
    } finally {
      setCreatingPatient(false)
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!patientId || !templateId) return

    setSubmitting(true)
    setError(null)
    setReport(null)
    try {
      const created = await createReport(patientId, templateId, answers)
      setReport(created)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível gerar o laudo.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <p>Carregando...</p>

  const progresso = template ? contarProgresso(template.schema_json, answers) : null

  return (
    <div>
      <PageHeader
        eyebrow="Atendimento"
        title="Novo Atendimento"
        description="Escolha o paciente e o modelo de laudo para gerar a avaliação."
      />

      {templates.length === 0 && (
        <Alert tone="warning" style={{ marginBottom: 'var(--np-space-5)' }}>
          Nenhum modelo de laudo cadastrado ainda. Cadastre um modelo (ex.: CARS, ATA, SNAP-IV) em
          "Modelos De Laudo" antes de gerar um atendimento.
        </Alert>
      )}

      <Card>
        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
          <div>
            {!showNewPatientForm ? (
              <>
                <Select
                  id="paciente"
                  label="Paciente"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="Selecione um paciente..."
                  options={patients.map((p) => ({ value: p.id, label: p.name }))}
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  icon={<Plus size={16} />}
                  style={{ marginTop: 'var(--np-space-2)', paddingLeft: 0 }}
                  onClick={() => setShowNewPatientForm(true)}
                >
                  Cadastrar Novo Paciente
                </Button>
              </>
            ) : (
              <Card tone="sunken" style={{ boxShadow: 'none' }}>
                <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
                  <Input
                    id="novo-paciente-nome"
                    label="Nome Completo Do Novo Paciente"
                    value={newPatientName}
                    onChange={(e) => setNewPatientName(e.target.value)}
                    required
                  />
                  <Input
                    id="novo-paciente-nascimento"
                    label="Data De Nascimento"
                    type="date"
                    value={newPatientBirth}
                    onChange={(e) => setNewPatientBirth(e.target.value)}
                    required
                  />
                  <div style={{ display: 'flex', gap: 'var(--np-space-3)' }}>
                    <Button
                      type="button"
                      onClick={handleCreatePatient}
                      disabled={creatingPatient || !newPatientName || !newPatientBirth}
                    >
                      {creatingPatient ? 'Cadastrando...' : 'Salvar Paciente'}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => setShowNewPatientForm(false)}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              </Card>
            )}
            {selectedPatient && !showNewPatientForm && (
              <p style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)', marginTop: 'var(--np-space-2)' }}>
                Atendimento para: <strong>{selectedPatient.name}</strong>
              </p>
            )}
          </div>

          <Select
            id="template"
            label="Modelo De Laudo / Escala"
            value={templateId}
            onChange={(e) => handleTemplateChange(e.target.value)}
            placeholder="Selecione um modelo..."
            options={templates.map((t) => ({ value: t.id, label: t.name }))}
            required
          />

          {template && progresso && (
            <ProgressBar
              label="Perguntas Respondidas"
              value={progresso.respondidas}
              max={Math.max(1, progresso.total)}
              caption={`${progresso.respondidas} de ${progresso.total}`}
            />
          )}

          {template && template.schema_json.areas.length > 4 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-2)' }}>
              {template.schema_json.areas.map((area) => (
                <a
                  key={area.key}
                  href={`#area-${area.key}`}
                  style={{
                    font: 'var(--np-type-caption)',
                    color: 'var(--np-text-brand)',
                    background: 'var(--np-surface-alt)',
                    padding: '4px 10px',
                    borderRadius: 'var(--np-radius-pill)',
                    textDecoration: 'none',
                  }}
                >
                  {area.label}
                </a>
              ))}
            </div>
          )}

          {template?.schema_json.areas.map((area) => (
            <Card key={area.key} id={`area-${area.key}`} tone="sunken" title={area.label} style={{ boxShadow: 'none', scrollMarginTop: 80 }}>
              <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
                {area.fields &&
                  area.fields.map((field) => (
                    <DynamicField
                      key={field.key}
                      field={field}
                      value={(answers[area.key] as Record<string, string | number | boolean>)?.[field.key]}
                      onChange={(value) => setFieldValue(area.key, field.key, value)}
                    />
                  ))}
                {area.age_brackets &&
                  area.age_brackets.map((bracket) => (
                    <Card key={bracket.label} title={bracket.label} padding="var(--np-space-4)" style={{ boxShadow: 'none' }}>
                      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
                        {bracket.fields.map((field) => (
                          <DynamicField
                            key={field.key}
                            field={field}
                            value={
                              (answers[area.key] as Record<string, Record<string, string>>)?.[bracket.label]?.[
                                field.key
                              ]
                            }
                            onChange={(value) =>
                              setBracketFieldValue(area.key, bracket.label, field.key, value as string | undefined)
                            }
                          />
                        ))}
                      </div>
                    </Card>
                  ))}
              </div>
            </Card>
          ))}

          {error && <Alert tone="danger">{error}</Alert>}

          <Button type="submit" disabled={submitting || !template || !patientId} style={{ justifySelf: 'start' }}>
            {submitting ? 'Gerando...' : 'Gerar Laudo'}
          </Button>
        </form>
      </Card>

      {report && template && <ResultadoLaudo report={report} template={template} onReportChange={setReport} />}
    </div>
  )
}

function ResultadoLaudo({
  report,
  template,
  onReportChange,
}: {
  report: Report
  template: ReportTemplate
  onReportChange: (report: Report) => void
}) {
  const navigate = useNavigate()
  const result = report.computed_json as ComputedResult
  const areas = template.schema_json.areas
  const labels = areas.map((a) => a.label)
  const values = areas.map((a) => result.scores?.[a.key] ?? 0)

  const [text, setText] = useState(report.generated_text ?? '')
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [textError, setTextError] = useState<string | null>(null)
  const [autoTried, setAutoTried] = useState(false)

  async function handleGenerateText() {
    setGenerating(true)
    setTextError(null)
    try {
      const updated = await generateReportText(report.id)
      setText(updated.generated_text ?? '')
      onReportChange(updated)
    } catch (err) {
      setTextError(
        err instanceof ApiError
          ? err.message
          : 'Não foi possível gerar o texto com IA. Verifique a configuração em "Configurações".',
      )
    } finally {
      setGenerating(false)
    }
  }

  // Assim que o laudo é calculado, já tenta gerar o texto por IA
  // automaticamente — a psicóloga só precisa revisar/editar depois.
  useEffect(() => {
    if (!report.generated_text && !autoTried) {
      setAutoTried(true)
      handleGenerateText()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report.id])

  async function handleSaveText() {
    setSaving(true)
    setTextError(null)
    try {
      const updated = await updateReportText(report.id, text)
      onReportChange(updated)
      navigate(`/pacientes/${report.patient_id}/historico`)
    } catch {
      setTextError('Não foi possível salvar o texto revisado.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDownloadPdf() {
    setDownloading(true)
    setTextError(null)
    try {
      await downloadReportPdf(report.id, `laudo_${template.schema_json.name}.pdf`)
    } catch {
      setTextError('Não foi possível baixar o PDF.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Card title="Resultado" style={{ marginTop: 'var(--np-space-6)' }}>
      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        {result.total !== undefined && (
          <p style={{ margin: 0 }}>
            <strong>Pontuação total:</strong> {result.total}
          </p>
        )}
        {result.classification && (
          <p style={{ margin: 0 }}>
            <strong>Classificação:</strong> <Badge tone="brand">{result.classification}</Badge>
          </p>
        )}
        {result.classifications && (
          <div>
            <strong>Classificação por área:</strong>
            <ul>
              {Object.entries(result.classifications).map(([areaKey, label]) => {
                const area = areas.find((a) => a.key === areaKey)
                return (
                  <li key={areaKey} style={{ marginBottom: 'var(--np-space-1)' }}>
                    {area?.label ?? areaKey}: <Badge tone="brand">{label ?? 'Sem classificação'}</Badge>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {result.areas && (
          <div>
            <strong>Idade de desenvolvimento estimada por área:</strong>
            <ul>
              {Object.entries(result.areas).map(([areaKey, areaResult]) => {
                const area = areas.find((a) => a.key === areaKey)
                return (
                  <li key={areaKey} style={{ marginBottom: 'var(--np-space-1)' }}>
                    {area?.label ?? areaKey}: {areaResult.developmental_age_label} (
                    {areaResult.percentage}% da idade cronológica) —{' '}
                    <Badge tone="brand">{areaResult.classification ?? 'Sem classificação'}</Badge>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {!result.areas && (
          <Card
            tone="sunken"
            title={template.schema_json.name}
            subtitle="Pontuação Por Área"
            style={{ boxShadow: 'none', maxWidth: 640 }}
          >
            <ScoreChart type={template.schema_json.chart.type} labels={labels} values={values} title={template.schema_json.name} />
          </Card>
        )}

        <div>
          <h3 style={{ font: 'var(--np-type-section)', marginBottom: 'var(--np-space-2)' }}>
            Texto Do Laudo (Gerado Por IA — Revisável)
          </h3>
          {generating ? (
            <Alert
              tone="consent"
              icon={<Loader2 size={22} style={{ animation: 'np-spin 0.8s linear infinite' }} />}
              title="Gerando texto com IA..."
              style={{ marginBottom: 'var(--np-space-3)' }}
            >
              Isso pode levar alguns segundos. A sugestão aparece automaticamente na caixa de texto
              abaixo assim que estiver pronta.
            </Alert>
          ) : (
            <Alert tone="info" icon={<Sparkles size={18} />} style={{ marginBottom: 'var(--np-space-3)' }}>
              O texto abaixo é uma sugestão gerada por IA a partir da pontuação calculada. Revise e
              edite livremente antes de considerá-lo final — nada é exportado sem essa revisão.
            </Alert>
          )}

          <Button
            type="button"
            variant="outline"
            icon={
              generating ? (
                <Loader2 size={16} style={{ animation: 'np-spin 0.8s linear infinite' }} />
              ) : (
                <Sparkles size={16} />
              )
            }
            onClick={handleGenerateText}
            disabled={generating}
            style={{ marginBottom: 'var(--np-space-3)' }}
          >
            {generating ? 'Gerando com IA...' : text ? 'Gerar Novamente Com IA' : 'Gerar Texto Com IA'}
          </Button>

          {textError && (
            <Alert tone="danger" style={{ marginBottom: 'var(--np-space-3)' }}>
              {textError}{' '}
              <Link to="/configuracoes" style={{ color: 'inherit', fontWeight: 'bold' }}>
                Ir para Configurações
              </Link>
            </Alert>
          )}

          <textarea
            id="generated-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{
              width: '100%',
              minHeight: 220,
              padding: 'var(--np-space-3) var(--np-field-pad-x)',
              background: 'var(--np-surface)',
              border: '1px solid var(--np-border-strong)',
              borderRadius: 'var(--np-radius-sm)',
              font: 'var(--np-type-body)',
              color: 'var(--np-text)',
              resize: 'vertical',
              marginBottom: 'var(--np-space-3)',
            }}
            placeholder="Clique em “Gerar Texto Com IA” ou escreva o texto do laudo manualmente."
          />

          <div style={{ display: 'flex', gap: 'var(--np-space-3)', flexWrap: 'wrap' }}>
            <Button type="button" onClick={handleSaveText} disabled={saving} icon={<FileText size={16} />}>
              {saving ? 'Salvando...' : 'Salvar Texto Revisado'}
            </Button>
            <Button type="button" variant="outline" onClick={handleDownloadPdf} disabled={downloading} icon={<Download size={16} />}>
              {downloading ? 'Gerando PDF...' : 'Baixar PDF (Com Gráficos)'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  )
}
