import { Camera, Trash2 } from 'lucide-react'
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
  Report,
  ReportTemplate,
} from '../api/types'
import { Alert, Badge, Button, buttonStyle, Card, PageHeader } from '../components/ds'
import { EnvioDePdfsParaIA } from '../components/EnvioDePdfsParaIA'
import { FormulariosDeResponsaveis } from '../components/pacientes/FormulariosDeResponsaveis'
import { SecoesClinicasForm } from '../components/pacientes/SecoesClinicasForm'
import styles from './Page.module.css'


export default function HistoricoPaciente() {
  const { id } = useParams<{ id: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [reports, setReports] = useState<Report[]>([])
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

  function nomeDoTemplate(report: Report) {
    return report.template_name_override ?? templates.find((t) => t.id === report.template_id)?.name ?? 'Modelo removido'
  }

  // Laudo feito com um modelo de protocolo próprio (Configurações): reabre
  // na tela do atendimento configurável.
  function ehModeloDeProtocolo(report: Report) {
    const template = templates.find((t) => t.id === report.template_id)
    return (template?.schema_json as { rule_type?: string } | undefined)?.rule_type === 'protocolo'
  }

  function ehRelatorioIA(report: Report) {
    const template = templates.find((t) => t.id === report.template_id)
    return (template?.schema_json as { rule_type?: string } | undefined)?.rule_type === 'relatorio_ia_pdf'
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

  function toggleClinical(reportId: string) {
    setClinicalOpenId((prev) => (prev === reportId ? null : reportId))
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
      {id && <FormulariosDeResponsaveis patientId={id} />}

      {error && <Alert tone="danger">{error}</Alert>}

      {id && <EnvioDePdfsParaIA patientId={id} />}

      <Card title="Protocolos Do Paciente" style={{ marginTop: 'var(--np-space-5)' }}>
        {!error && reports.length === 0 && (
          <p style={{ color: 'var(--np-text-muted)' }}>Nenhum protocolo registrado para este paciente ainda. Clique em "+ Novo Protocolo Para Este Paciente" para começar.</p>
        )}

        {reports.length > 0 && (
          <>
            <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
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
                            {ehRelatorioIA(report) && (
                              <>
                                <Link className={styles.rowLink} to={`/pacientes/${id}/relatorio-ia/${report.id}`}>
                                  Abrir Relatório
                                </Link>{' '}
                              </>
                            )}
                            {ehModeloDeProtocolo(report) && (
                              <>
                                <Link className={styles.rowLink} to={`/atendimento/protocolo/${report.template_id}?laudo=${report.id}`}>
                                  Abrir Protocolo
                                </Link>{' '}
                              </>
                            )}
                            <button type="button" className={styles.rowLink} onClick={() => startEdit(report)}>
                              Editar
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
