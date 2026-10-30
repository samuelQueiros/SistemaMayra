/** Diálogo para escolher qual relatório do paciente baixar, em PDF ou Word. */
import { useEffect, useState } from 'react'
import { Download, FileText, X } from 'lucide-react'
import { ApiError } from '../../api/client'
import { downloadReportDocx, downloadReportPdf, listReports } from '../../api/reports'
import { listTemplates } from '../../api/templates'
import type { Patient, ReportResumo, ReportTemplate } from '../../api/types'
import { Alert, Badge, Button, Card, IconButton } from '../ds'
import { nomeParaExibicao } from '../../utils/exibicao'

// "Baixar PDF/Word" da lista de pacientes: mostra os relatórios do paciente
// (mais recente primeiro, destacado) para escolher qual baixar.
export function BaixarRelatorioDialog({ patient, onClose }: { patient: Patient; onClose: () => void }) {
  const [reports, setReports] = useState<ReportResumo[] | null>(null)
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [baixando, setBaixando] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listReports(patient.id), listTemplates()])
      .then(([r, t]) => {
        setReports([...r].sort((a, b) => b.created_at.localeCompare(a.created_at)))
        setTemplates(t)
      })
      .catch(() => setErro('Não foi possível carregar os relatórios deste paciente.'))
  }, [patient.id])

  useEffect(() => {
    const fechar = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', fechar)
    return () => window.removeEventListener('keydown', fechar)
  }, [onClose])

  const nomeDoModelo = (r: ReportResumo) => r.template_name_override ?? templates.find((t) => t.id === r.template_id)?.name ?? 'Relatório'

  async function baixar(r: ReportResumo, formato: 'pdf' | 'docx') {
    setErro(null)
    setBaixando(`${r.id}:${formato}`)
    const nome = `relatorio_${patient.name.replace(/\s+/g, '_')}.${formato}`
    try {
      if (formato === 'pdf') await downloadReportPdf(r.id, nome)
      else await downloadReportDocx(r.id, nome)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : `Não foi possível gerar o ${formato === 'pdf' ? 'PDF' : 'Word'}.`)
    } finally {
      setBaixando(null)
    }
  }

  const nome = nomeParaExibicao(patient.name)

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Baixar relatório de ${nome}`}
      className="dialog-backdrop"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <Card
        title={`Baixar relatório — ${nome}`}
        subtitle="Escolha o relatório e o formato."
        action={<IconButton label="Fechar" icon={<X />} onClick={onClose} />}
        style={{ width: 'min(640px, 100%)', maxHeight: '85vh', overflowY: 'auto' }}
      >
        {erro && <Alert tone="danger" style={{ marginBottom: 'var(--s-3)' }}>{erro}</Alert>}
        {reports === null && !erro && <p className="text-2">Carregando…</p>}
        {reports?.length === 0 && <p className="text-2">Este paciente ainda não tem relatórios.</p>}
        <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
          {reports?.map((r, i) => (
            <div key={r.id} className={`list-row${i === 0 ? ' list-row-highlight' : ''}`}>
              <div style={{ flex: 1, minWidth: 180 }}>
                <div className="list-row-title">
                  {nomeDoModelo(r)} {i === 0 && <Badge tone="brand">Mais recente</Badge>}
                </div>
                <div className="list-row-meta">{new Date(r.created_at).toLocaleString('pt-BR')}</div>
              </div>
              <div style={{ display: 'flex', gap: 'var(--s-2)' }}>
                <Button
                  size="sm"
                  variant="tonal"
                  icon={<Download />}
                  loading={baixando === `${r.id}:pdf`}
                  loadingLabel="Gerando…"
                  disabled={!!baixando}
                  onClick={() => baixar(r, 'pdf')}
                >
                  PDF
                </Button>
                <Button
                  size="sm"
                  variant="tonal"
                  icon={<FileText />}
                  loading={baixando === `${r.id}:docx`}
                  loadingLabel="Gerando…"
                  disabled={!!baixando}
                  onClick={() => baixar(r, 'docx')}
                >
                  Word
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
