import { Camera, Download, FileText, Trash2 } from 'lucide-react'
import { Fragment, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  deletePatientPhoto,
  fetchPatientPhotoUrl,
  getPatient,
  listPatientPhotos,
  uploadPatientPhoto,
} from '../api/patients'
import {
  downloadConsolidatedPdf,
  downloadReportDocx,
  downloadReportPdf,
  downloadSavedConsolidatedPdf,
  getReportLogs,
  listCidCodes,
  listConsolidatedReports,
  listReports,
  updateClinicalSections,
  updateReportEdit,
} from '../api/reports'
import { listTemplates } from '../api/templates'
import type {
  CidCode,
  ClinicalSections,
  ConsolidatedReport,
  Patient,
  PatientPhoto,
  Report,
  ReportChangeLog,
  ReportTemplate,
} from '../api/types'
import { Alert, Badge, Button, buttonStyle, Card, Checkbox, Input, PageHeader, Textarea } from '../components/ds'
import styles from './Page.module.css'

const ENCAMINHAMENTOS_SUGERIDOS = [
  'Neuropediatra',
  'Avaliação Neuropsicológica',
  'Fonoaudiologia',
  'Terapia Ocupacional',
  'Psicopedagogia',
]

export default function HistoricoPaciente() {
  const { id } = useParams<{ id: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [reports, setReports] = useState<Report[]>([])
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [consolidating, setConsolidating] = useState(false)
  const [consolidateError, setConsolidateError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editClassification, setEditClassification] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  const [logsOpenId, setLogsOpenId] = useState<string | null>(null)
  const [logs, setLogs] = useState<ReportChangeLog[]>([])
  const [loadingLogs, setLoadingLogs] = useState(false)

  const [clinicalOpenId, setClinicalOpenId] = useState<string | null>(null)

  function carregar() {
    if (!id) return
    setLoading(true)
    Promise.all([getPatient(id), listReports(id), listTemplates()])
      .then(([p, r, t]) => {
        setPatient(p)
        setReports(r)
        setTemplates(t)
      })
      .catch(() => setError('Não foi possível carregar o histórico deste paciente.'))
      .finally(() => setLoading(false))
  }

  useEffect(carregar, [id])

  function nomeDoTemplate(report: Report) {
    return report.template_name_override ?? templates.find((t) => t.id === report.template_id)?.name ?? 'Modelo removido'
  }

  function classificacaoResumo(report: Report) {
    if (report.classification_override) return report.classification_override
    const computed = report.computed_json
    if (!computed) return '—'
    if (computed.classification) return computed.classification
    if (computed.classifications) {
      return Object.values(computed.classifications).filter(Boolean).join(' / ') || '—'
    }
    return '—'
  }

  function toggleSelected(reportId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(reportId)) next.delete(reportId)
      else next.add(reportId)
      return next
    })
  }

  function startEdit(report: Report) {
    setEditingId(report.id)
    setEditName(nomeDoTemplate(report))
    setEditClassification(classificacaoResumo(report))
  }

  async function saveEdit(report: Report) {
    setSavingEdit(true)
    try {
      const updated = await updateReportEdit(report.id, {
        template_name_override: editName,
        classification_override: editClassification,
      })
      setReports((prev) => prev.map((r) => (r.id === report.id ? updated : r)))
      setEditingId(null)
    } catch {
      setError('Não foi possível salvar a edição.')
    } finally {
      setSavingEdit(false)
    }
  }

  async function toggleLogs(reportId: string) {
    if (logsOpenId === reportId) {
      setLogsOpenId(null)
      return
    }
    setLogsOpenId(reportId)
    setLoadingLogs(true)
    try {
      setLogs(await getReportLogs(reportId))
    } catch {
      setLogs([])
    } finally {
      setLoadingLogs(false)
    }
  }

  function toggleClinical(reportId: string) {
    setClinicalOpenId((prev) => (prev === reportId ? null : reportId))
  }

  const [consolidatedRefreshKey, setConsolidatedRefreshKey] = useState(0)

  async function handleConsolidatedPdf() {
    if (!id || selectedIds.size === 0) return
    setConsolidating(true)
    setConsolidateError(null)
    try {
      await downloadConsolidatedPdf(id, Array.from(selectedIds), `protocolo_consolidado_${patient?.name ?? id}.pdf`)
      setConsolidatedRefreshKey((k) => k + 1)
    } catch (err) {
      setConsolidateError(
        err instanceof ApiError ? err.message : 'Não foi possível gerar o PDF consolidado.',
      )
    } finally {
      setConsolidating(false)
    }
  }

  async function handleDownloadReport(report: Report, formato: 'pdf' | 'docx') {
    setError(null)
    const nomeArquivo = `relatorio_${(patient?.name ?? nomeDoTemplate(report)).replace(/\s+/g, '_')}.${formato}`
    try {
      if (formato === 'pdf') await downloadReportPdf(report.id, nomeArquivo)
      else await downloadReportDocx(report.id, nomeArquivo)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Não foi possível gerar o ${formato === 'pdf' ? 'PDF' : 'Word'}.`)
    }
  }

  if (loading) return <p>Carregando...</p>

  return (
    <div>
      <PageHeader
        eyebrow="Histórico"
        title={patient ? patient.name : `Paciente #${id}`}
        actions={
          <Link to={`/atendimento/novo?paciente=${id}`} style={buttonStyle('primary')}>
            + Novo Protocolo Para Este Paciente
          </Link>
        }
      />

      {id && <FotosDoPaciente patientId={id} />}

      {error && <Alert tone="danger">{error}</Alert>}

      <Card title="Protocolos Do Paciente" style={{ marginTop: 'var(--np-space-5)' }}>
        {!error && reports.length === 0 && (
          <p style={{ color: 'var(--np-text-muted)' }}>Nenhum protocolo registrado para este paciente ainda. Clique em "+ Novo Protocolo Para Este Paciente" para começar.</p>
        )}

        {reports.length > 0 && (
          <>
            <p style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>
              Marque um ou mais protocolos abaixo para gerar um único PDF consolidado, escrito por IA a
              partir de todos eles.
            </p>
            <div style={{ marginBottom: 'var(--np-space-3)' }}>
              <Button
                type="button"
                onClick={handleConsolidatedPdf}
                disabled={selectedIds.size === 0 || consolidating}
                icon={<FileText size={16} />}
              >
                {consolidating
                  ? 'Gerando PDF Consolidado...'
                  : `Gerar PDF Consolidado (${selectedIds.size} Selecionado${selectedIds.size === 1 ? '' : 's'})`}
              </Button>
            </div>
            {consolidateError && <Alert tone="danger" style={{ marginBottom: 'var(--np-space-3)' }}>{consolidateError}</Alert>}

            <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th></th>
                  <th>Data</th>
                  <th>Modelo Usado</th>
                  <th>Classificação</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <Fragment key={report.id}>
                    <tr>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(report.id)}
                          onChange={() => toggleSelected(report.id)}
                        />
                      </td>
                      <td>{new Date(report.created_at).toLocaleString('pt-BR')}</td>

                      {editingId === report.id ? (
                        <>
                          <td>
                            <input value={editName} onChange={(e) => setEditName(e.target.value)} />
                          </td>
                          <td>
                            <input
                              value={editClassification}
                              onChange={(e) => setEditClassification(e.target.value)}
                            />
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => saveEdit(report)}
                              disabled={savingEdit}
                              style={{ marginRight: 'var(--np-space-2)' }}
                            >
                              {savingEdit ? 'Salvando...' : 'Salvar'}
                            </Button>
                            <Button type="button" size="sm" variant="outline" onClick={() => setEditingId(null)}>
                              Cancelar
                            </Button>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>{nomeDoTemplate(report)}</td>
                          <td>
                            <Badge tone="brand">{classificacaoResumo(report)}</Badge>
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <button type="button" className={styles.rowLink} onClick={() => startEdit(report)}>
                              Editar
                            </button>{' '}
                            <button type="button" className={styles.rowLink} onClick={() => toggleLogs(report.id)}>
                              {logsOpenId === report.id ? 'Ocultar Logs' : 'Ver Logs'}
                            </button>{' '}
                            <button type="button" className={styles.rowLink} onClick={() => toggleClinical(report.id)}>
                              {clinicalOpenId === report.id ? 'Ocultar Seções Clínicas' : 'Seções Clínicas'}
                            </button>{' '}
                            <button
                              type="button"
                              className={styles.rowLink}
                              onClick={() => handleDownloadReport(report, 'pdf')}
                            >
                              Baixar PDF
                            </button>{' '}
                            <button
                              type="button"
                              className={styles.rowLink}
                              onClick={() => handleDownloadReport(report, 'docx')}
                            >
                              Baixar Word
                            </button>
                          </td>
                        </>
                      )}
                    </tr>
                    {logsOpenId === report.id && (
                      <tr>
                        <td></td>
                        <td colSpan={4}>
                          <Card tone="sunken" style={{ boxShadow: 'none' }}>
                            {loadingLogs && <p>Carregando logs...</p>}
                            {!loadingLogs && logs.length === 0 && <p>Nenhuma edição registrada para este protocolo.</p>}
                            {!loadingLogs && logs.length > 0 && (
                              <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                                {logs.map((log) => (
                                  <li key={log.id}>
                                    {new Date(log.created_at).toLocaleString('pt-BR')} — {log.psychologist_name}{' '}
                                    alterou <strong>{log.field === 'template_name_override' ? 'Modelo' : 'Classificação'}</strong>:{' '}
                                    "{log.old_value ?? '(vazio)'}" → "{log.new_value}"
                                  </li>
                                ))}
                              </ul>
                            )}
                          </Card>
                        </td>
                      </tr>
                    )}
                    {clinicalOpenId === report.id && (
                      <tr>
                        <td></td>
                        <td colSpan={4}>
                          <SecoesClinicasForm
                            report={report}
                            onSaved={(updated) =>
                              setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
                            }
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
            </div>
          </>
        )}
      </Card>

      {id && patient && (
        <ListaDeConsolidados patientId={id} patientName={patient.name} refreshKey={consolidatedRefreshKey} />
      )}
    </div>
  )
}

function ListaDeConsolidados({
  patientId,
  patientName,
  refreshKey,
}: {
  patientId: string
  patientName: string
  refreshKey: number
}) {
  const [consolidados, setConsolidados] = useState<ConsolidatedReport[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listConsolidatedReports(patientId)
      .then(setConsolidados)
      .catch(() => setConsolidados([]))
      .finally(() => setLoading(false))
  }, [patientId, refreshKey])

  if (loading || consolidados.length === 0) return null

  return (
    <Card title="Pareceres Consolidados Já Gerados" style={{ marginTop: 'var(--np-space-5)' }}>
      <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'grid', gap: 'var(--np-space-3)' }}>
        {consolidados.map((c) => (
          <li key={c.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--np-space-3)' }}>
            <span style={{ font: 'var(--np-type-body)', color: 'var(--np-text-muted)' }}>
              {new Date(c.created_at).toLocaleString('pt-BR')} — {c.report_ids.length} protocolo
              {c.report_ids.length === 1 ? '' : 's'} consolidado{c.report_ids.length === 1 ? '' : 's'}
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              icon={<Download size={14} />}
              onClick={() => downloadSavedConsolidatedPdf(c.id, `protocolo_consolidado_${patientName}.pdf`)}
            >
              Baixar PDF
            </Button>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function FotosDoPaciente({ patientId }: { patientId: string }) {
  const [photos, setPhotos] = useState<PatientPhoto[]>([])
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function carregar() {
    setLoading(true)
    listPatientPhotos(patientId)
      .then(setPhotos)
      .catch(() => setError('Não foi possível carregar as fotos do paciente.'))
      .finally(() => setLoading(false))
  }

  useEffect(carregar, [patientId])

  useEffect(() => {
    let cancelado = false
    photos.forEach((photo) => {
      if (urls[photo.id]) return
      fetchPatientPhotoUrl(patientId, photo.id)
        .then((url) => {
          if (!cancelado) setUrls((prev) => ({ ...prev, [photo.id]: url }))
        })
        .catch(() => {})
    })
    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photos])

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const created = await uploadPatientPhoto(patientId, file)
      setPhotos((prev) => [...prev, created])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível enviar a foto.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDelete(photoId: string) {
    try {
      await deletePatientPhoto(patientId, photoId)
      setPhotos((prev) => prev.filter((p) => p.id !== photoId))
    } catch {
      setError('Não foi possível excluir a foto.')
    }
  }

  if (loading) return null

  return (
    <Card title="Fotos Do Paciente" subtitle="Usadas no relatório em PDF e Word (a primeira foto vai no cabeçalho)." style={{ marginTop: 'var(--np-space-5)' }}>
      {error && <Alert tone="danger" style={{ marginBottom: 'var(--np-space-3)' }}>{error}</Alert>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)', marginBottom: 'var(--np-space-4)' }}>
        {photos.map((photo) => (
          <div key={photo.id} style={{ textAlign: 'center' }}>
            {urls[photo.id] ? (
              <img
                src={urls[photo.id]}
                alt={photo.caption ?? 'Foto do paciente'}
                style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 'var(--np-radius-md)', border: '2px solid var(--np-white)', boxShadow: 'var(--np-shadow-xs)' }}
              />
            ) : (
              <div style={{ width: 100, height: 100, background: 'var(--np-surface-sunken)', borderRadius: 'var(--np-radius-md)' }} />
            )}
            <button
              type="button"
              onClick={() => handleDelete(photo.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                margin: '6px auto 0',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--np-danger)',
                font: 'var(--np-type-caption)',
              }}
            >
              <Trash2 size={12} /> Excluir
            </button>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--np-space-3)', flexWrap: 'wrap' }}>
        <input type="file" accept=".jpg,.jpeg,.png,.webp" ref={fileInputRef} />
        <Button type="button" size="sm" icon={<Camera size={16} />} onClick={handleUpload} disabled={uploading}>
          {uploading ? 'Enviando...' : 'Adicionar Foto'}
        </Button>
      </div>
    </Card>
  )
}

function SecoesClinicasForm({
  report,
  onSaved,
}: {
  report: Report
  onSaved: (updated: Report) => void
}) {
  const atuais = report.clinical_sections_json ?? {}
  const [form, setForm] = useState<ClinicalSections>(atuais)
  const [cidCodes, setCidCodes] = useState<CidCode[]>([])
  const [outraHipotese, setOutraHipotese] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    listCidCodes()
      .then(setCidCodes)
      .catch(() => setCidCodes([]))
  }, [])

  function setCampo<K extends keyof ClinicalSections>(campo: K, valor: ClinicalSections[K]) {
    setForm((prev) => ({ ...prev, [campo]: valor }))
  }

  function toggleEncaminhamento(nome: string) {
    setForm((prev) => {
      const atuais = prev.encaminhamentos ?? []
      const proximos = atuais.includes(nome) ? atuais.filter((e) => e !== nome) : [...atuais, nome]
      return { ...prev, encaminhamentos: proximos }
    })
  }

  function toggleHipotese(label: string, cid: string | null) {
    setForm((prev) => {
      const atuais = prev.diagnostic_hypotheses ?? []
      const jaMarcada = atuais.some((h) => h.label === label)
      const proximas = jaMarcada
        ? atuais.filter((h) => h.label !== label)
        : [...atuais, { label, cid, selected: atuais.length === 0 }]
      return { ...prev, diagnostic_hypotheses: proximas }
    })
  }

  // Só a hipótese marcada aqui aparece no PDF final — as demais ficam
  // registradas como "investigadas", mas não impressas no relatório.
  function selecionarHipotesePrincipal(label: string) {
    setForm((prev) => ({
      ...prev,
      diagnostic_hypotheses: (prev.diagnostic_hypotheses ?? []).map((h) => ({ ...h, selected: h.label === label })),
    }))
  }

  function adicionarOutraHipotese() {
    if (!outraHipotese.trim()) return
    toggleHipotese(outraHipotese.trim(), null)
    setOutraHipotese('')
  }

  async function handleSalvar() {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await updateClinicalSections(report.id, form)
      onSaved(updated)
      setSuccess(true)
    } catch {
      setError('Não foi possível salvar as seções clínicas.')
    } finally {
      setSaving(false)
    }
  }

  const hipotesesMarcadas = new Set((form.diagnostic_hypotheses ?? []).map((h) => h.label))

  return (
    <Card tone="sunken" style={{ boxShadow: 'none', textAlign: 'left' }}>
      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <Textarea label="Anamnese Inicial" value={form.anamnese ?? ''} onChange={(e) => setCampo('anamnese', e.target.value)} rows={3} />
        <Textarea
          label="Histórico De Desenvolvimento"
          value={form.historico_desenvolvimento ?? ''}
          onChange={(e) => setCampo('historico_desenvolvimento', e.target.value)}
          rows={3}
        />
        <Textarea
          label="Encaminhamento, Histórico E Queixas"
          value={form.encaminhamento_queixas ?? ''}
          onChange={(e) => setCampo('encaminhamento_queixas', e.target.value)}
          rows={3}
        />
        <Textarea label="Metodologia" value={form.metodologia ?? ''} onChange={(e) => setCampo('metodologia', e.target.value)} rows={2} />
        <Textarea
          label="Estudo De Caso E Observações Clínicas"
          value={form.estudo_de_caso ?? ''}
          onChange={(e) => setCampo('estudo_de_caso', e.target.value)}
          rows={4}
        />

        <div>
          <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
            Hipóteses Diagnósticas Investigadas
          </span>
          <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
            {cidCodes.map((c) => (
              <Checkbox
                key={c.label}
                label={`${c.label} (CID: ${c.cid})`}
                checked={hipotesesMarcadas.has(c.label)}
                onChange={() => toggleHipotese(c.label, c.cid)}
              />
            ))}
            {(form.diagnostic_hypotheses ?? [])
              .filter((h) => !cidCodes.some((c) => c.label === h.label))
              .map((h) => (
                <Checkbox key={h.label} label={h.label} checked onChange={() => toggleHipotese(h.label, h.cid ?? null)} />
              ))}
          </div>
          <div style={{ display: 'flex', gap: 'var(--np-space-2)', marginTop: 'var(--np-space-3)' }}>
            <Input placeholder="Outra hipótese..." value={outraHipotese} onChange={(e) => setOutraHipotese(e.target.value)} style={{ flex: 1 }} />
            <Button type="button" variant="outline" onClick={adicionarOutraHipotese}>
              Adicionar
            </Button>
          </div>

          {(form.diagnostic_hypotheses ?? []).length > 0 && (
            <div style={{ marginTop: 'var(--np-space-4)' }}>
              <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
                Hipótese Selecionada Para Este Paciente (única que aparece no PDF)
              </span>
              <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
                {(form.diagnostic_hypotheses ?? []).map((h) => (
                  <label key={h.label} style={{ display: 'flex', gap: 'var(--np-space-2)', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="hipotese-principal"
                      checked={!!h.selected}
                      onChange={() => selecionarHipotesePrincipal(h.label)}
                    />
                    <span>
                      {h.label}
                      {h.cid ? ` (CID: ${h.cid})` : ''}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <Textarea
          label="Plano De Intervenção"
          value={form.plano_intervencao ?? ''}
          onChange={(e) => setCampo('plano_intervencao', e.target.value)}
          rows={3}
        />

        <div>
          <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
            Encaminhamentos
          </span>
          <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
            {ENCAMINHAMENTOS_SUGERIDOS.map((nome) => (
              <Checkbox
                key={nome}
                label={nome}
                checked={(form.encaminhamentos ?? []).includes(nome)}
                onChange={() => toggleEncaminhamento(nome)}
              />
            ))}
          </div>
        </div>

        <Textarea
          label="Considerações Finais"
          value={form.consideracoes_finais ?? ''}
          onChange={(e) => setCampo('consideracoes_finais', e.target.value)}
          rows={3}
        />

        {error && <Alert tone="danger">{error}</Alert>}
        {success && <Alert tone="success">Seções clínicas salvas com sucesso.</Alert>}
        <Button type="button" onClick={handleSalvar} disabled={saving} style={{ justifySelf: 'start' }}>
          {saving ? 'Salvando...' : 'Salvar Seções Clínicas'}
        </Button>
      </div>
    </Card>
  )
}
