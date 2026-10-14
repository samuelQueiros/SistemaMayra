import { Camera, Download, Ellipsis, FileText, Pencil, Plus, Sparkles, Stethoscope, Trash2 } from 'lucide-react'
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
  downloadReportDocx,
  downloadReportPdf,
  listReports,
  updateReportEdit,
} from '../api/reports'
import { listTemplates } from '../api/templates'
import type {
  Patient,
  PatientPhoto,
  ReportResumo,
  ReportTemplate,
} from '../api/types'
import { Alert, Badge, Button, buttonClass, Card, Menu, PageHeader } from '../components/ds'
import { FormulariosDeResponsaveis } from '../components/pacientes/FormulariosDeResponsaveis'
import { SecoesClinicasForm } from '../components/pacientes/SecoesClinicasForm'
import { idadeParaExibicao, nomeParaExibicao } from '../utils/exibicao'
import styles from './Page.module.css'


export default function HistoricoPaciente() {
  const { id } = useParams<{ id: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [reports, setReports] = useState<ReportResumo[]>([])
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editClassification, setEditClassification] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

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

  function nomeDoTemplate(report: ReportResumo) {
    return report.template_name_override ?? templates.find((t) => t.id === report.template_id)?.name ?? 'Modelo removido'
  }

  // Laudo feito com um modelo de protocolo próprio (Configurações): reabre
  // na tela do atendimento configurável.
  function ehModeloDeProtocolo(report: ReportResumo) {
    const template = templates.find((t) => t.id === report.template_id)
    return (template?.schema_json as { rule_type?: string } | undefined)?.rule_type === 'protocolo'
  }

  // Protocolo padrão (formulario-novo-paciente.html), manual ou gerado pelo Laudo Por IA.
  function ehProtocoloPadrao(report: ReportResumo) {
    const template = templates.find((t) => t.id === report.template_id)
    return (template?.schema_json as { rule_type?: string } | undefined)?.rule_type === 'custom_form'
  }

  function ehRelatorioIA(report: ReportResumo) {
    const template = templates.find((t) => t.id === report.template_id)
    return (template?.schema_json as { rule_type?: string } | undefined)?.rule_type === 'relatorio_ia_pdf'
  }

  function classificacaoResumo(report: ReportResumo) {
    if (report.classification_override) return report.classification_override
    const computed = report.computed_json
    if (!computed) return '—'
    if (computed.classification) return computed.classification
    if (computed.classifications) {
      return Object.values(computed.classifications).filter(Boolean).join(' / ') || '—'
    }
    return '—'
  }

  function startEdit(report: ReportResumo) {
    setEditingId(report.id)
    setEditName(nomeDoTemplate(report))
    setEditClassification(classificacaoResumo(report))
  }

  async function saveEdit(report: ReportResumo) {
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

  function toggleClinical(reportId: string) {
    setClinicalOpenId((prev) => (prev === reportId ? null : reportId))
  }

  async function handleDownloadReport(report: ReportResumo, formato: 'pdf' | 'docx') {
    setError(null)
    const nomeArquivo = `relatorio_${(patient?.name ?? nomeDoTemplate(report)).replace(/\s+/g, '_')}.${formato}`
    try {
      if (formato === 'pdf') await downloadReportPdf(report.id, nomeArquivo)
      else await downloadReportDocx(report.id, nomeArquivo)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Não foi possível gerar o ${formato === 'pdf' ? 'PDF' : 'Word'}.`)
    }
  }

  if (loading) return <p className="text-2">Carregando…</p>

  return (
    <div>
      <PageHeader
        eyebrow="Pacientes · Histórico"
        title={patient ? nomeParaExibicao(patient.name) : `Paciente #${id}`}
        description={
          patient
            ? [idadeParaExibicao(patient.birth_date), `nascimento em ${new Date(`${patient.birth_date}T00:00:00`).toLocaleDateString('pt-BR')}`].filter(Boolean).join(' · ')
            : undefined
        }
        actions={
          <Link to={`/atendimento/novo?paciente=${id}`} className={buttonClass('primary', 'lg')}>
            <Plus aria-hidden="true" /> Novo protocolo para este paciente
          </Link>
        }
      />

      {id && <FotosDoPaciente patientId={id} />}
      {id && <FormulariosDeResponsaveis patientId={id} />}

      {error && <Alert tone="danger">{error}</Alert>}

      {id && (
        <Card title="Laudo por IA" style={{ marginTop: 'var(--s-5)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-4)', alignItems: 'center', justifyContent: 'space-between' }}>
            <p className="text-2" style={{ margin: 0, flex: '1 1 320px' }}>
              Envie os PDFs dos formulários e das escalas para gerar o estudo de caso e o laudo no protocolo padrão.
            </p>
            <Link to={`/laudo-ia?paciente=${id}`} className={buttonClass('tonal')}>
              <Sparkles aria-hidden="true" /> Gerar laudo com IA
            </Link>
          </div>
        </Card>
      )}

      <Card title="Protocolos do paciente" style={{ marginTop: 'var(--s-5)' }}>
        {!error && reports.length === 0 && (
          <p className="text-2" style={{ margin: 0 }}>Nenhum protocolo registrado para este paciente ainda. Clique em "Novo protocolo para este paciente" para começar.</p>
        )}

        {reports.length > 0 && (
          <>
            <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Modelo usado</th>
                  <th>Classificação</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <Fragment key={report.id}>
                    <tr>
                      <td style={{ whiteSpace: 'nowrap' }}>{new Date(report.created_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</td>

                      {editingId === report.id ? (
                        <>
                          <td>
                            <input className="input" aria-label="Modelo usado" value={editName} onChange={(e) => setEditName(e.target.value)} />
                          </td>
                          <td>
                            <input
                              className="input"
                              aria-label="Classificação"
                              value={editClassification}
                              onChange={(e) => setEditClassification(e.target.value)}
                            />
                          </td>
                          <td>
                            <div className={styles.rowActions} style={{ flexWrap: 'nowrap' }}>
                              <Button size="sm" onClick={() => saveEdit(report)} loading={savingEdit} loadingLabel="Salvando…">
                                Salvar
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditingId(null)} disabled={savingEdit}>
                                Cancelar
                              </Button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>{nomeDoTemplate(report)}</td>
                          <td>
                            {classificacaoResumo(report) === '—' ? (
                              <span className="text-2">—</span>
                            ) : (
                              <Badge tone="brand">{classificacaoResumo(report)}</Badge>
                            )}
                          </td>
                          <td>
                            <div className={styles.rowActions} style={{ justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                              {ehRelatorioIA(report) && (
                                <Link className={buttonClass('secondary', 'sm')} to={`/pacientes/${id}/relatorio-ia/${report.id}`}>
                                  Abrir relatório
                                </Link>
                              )}
                              {ehProtocoloPadrao(report) && (
                                <Link className={buttonClass('secondary', 'sm')} to={`/atendimento/novo?laudo=${report.id}`}>
                                  Abrir protocolo
                                </Link>
                              )}
                              {ehModeloDeProtocolo(report) && (
                                <Link className={buttonClass('secondary', 'sm')} to={`/atendimento/protocolo/${report.template_id}?laudo=${report.id}`}>
                                  Abrir protocolo
                                </Link>
                              )}
                              <Button size="sm" variant="tonal" icon={<Download />} aria-label="Baixar PDF" onClick={() => handleDownloadReport(report, 'pdf')}>
                                PDF
                              </Button>
                              <Button size="sm" variant="tonal" icon={<FileText />} aria-label="Baixar Word" onClick={() => handleDownloadReport(report, 'docx')}>
                                Word
                              </Button>
                              <Menu
                                label={`Mais ações do protocolo de ${new Date(report.created_at).toLocaleDateString('pt-BR')}`}
                                icon={<Ellipsis />}
                                items={[
                                  { label: 'Editar', icon: <Pencil />, onSelect: () => startEdit(report) },
                                  {
                                    label: clinicalOpenId === report.id ? 'Ocultar seções clínicas' : 'Seções clínicas',
                                    icon: <Stethoscope />,
                                    onSelect: () => toggleClinical(report.id),
                                  },
                                ]}
                              />
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                    {clinicalOpenId === report.id && (
                      <tr>
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

    </div>
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
    <Card title="Fotos do paciente" subtitle="Usadas no relatório em PDF e Word (a primeira foto vai no cabeçalho)." style={{ marginTop: 'var(--s-5)' }}>
      {error && <Alert tone="danger" style={{ marginBottom: 'var(--s-3)' }}>{error}</Alert>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)', marginBottom: 'var(--s-4)' }}>
        {photos.map((photo) => (
          <div key={photo.id} style={{ textAlign: 'center' }}>
            {urls[photo.id] ? (
              <img
                src={urls[photo.id]}
                alt={photo.caption ?? 'Foto do paciente'}
                style={{ width: 112, height: 112, objectFit: 'cover', borderRadius: 'var(--r-md)', border: '1px solid var(--divider)', display: 'block' }}
              />
            ) : (
              <div style={{ width: 112, height: 112, background: 'var(--n-50)', borderRadius: 'var(--r-md)' }} />
            )}
            <Button size="sm" variant="danger-ghost" icon={<Trash2 />} aria-label="Excluir foto" onClick={() => handleDelete(photo.id)} style={{ marginTop: 'var(--s-1)' }}>
              Excluir
            </Button>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-3)', flexWrap: 'wrap' }}>
        <input type="file" accept=".jpg,.jpeg,.png,.webp" ref={fileInputRef} aria-label="Escolher foto do paciente" />
        <Button size="sm" variant="secondary" icon={<Camera />} onClick={handleUpload} loading={uploading} loadingLabel="Enviando…">
          Adicionar foto
        </Button>
      </div>
    </Card>
  )
}
