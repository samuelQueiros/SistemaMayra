import { useEffect, useState } from 'react'
import { Download, FileText, X } from 'lucide-react'
import { ApiError } from '../../api/client'
import { downloadReportDocx, downloadReportPdf, listReports } from '../../api/reports'
import { listTemplates } from '../../api/templates'
import type { Patient, Report, ReportTemplate } from '../../api/types'
import { Alert, Badge, Button, Card, IconButton } from '../ds'

// "Baixar PDF/Word" da lista de pacientes: mostra os relatórios do paciente
// (mais recente primeiro, destacado) para escolher qual baixar.
export function BaixarRelatorioDialog({ patient, onClose }: { patient: Patient; onClose: () => void }) {
  const [reports, setReports] = useState<Report[] | null>(null)
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

  const nomeDoModelo = (r: Report) => r.template_name_override ?? templates.find((t) => t.id === r.template_id)?.name ?? 'Relatório'

  async function baixar(r: Report, formato: 'pdf' | 'docx') {
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

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Baixar relatório de ${patient.name}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(20, 16, 40, 0.45)', display: 'grid', placeItems: 'center', padding: 16, zIndex: 50 }}
    >
      <Card
        title={`Baixar Relatório — ${patient.name}`}
        subtitle="Escolha o relatório e o formato."
        action={<IconButton label="Fechar" icon={<X size={18} />} variant="ghost" onClick={onClose} />}
        style={{ width: 'min(640px, 100%)', maxHeight: '85vh', overflowY: 'auto' }}
      >
        {erro && <Alert tone="danger" style={{ marginBottom: 'var(--np-space-3)' }}>{erro}</Alert>}
        {reports === null && !erro && <p>Carregando…</p>}
        {reports?.length === 0 && <p style={{ color: 'var(--np-text-muted)' }}>Este paciente ainda não tem relatórios.</p>}
        <div style={{ display: 'grid', gap: 'var(--np-space-3)' }}>
          {reports?.map((r, i) => (
            <div
              key={r.id}
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--np-space-3)',
                alignItems: 'center',
                padding: 'var(--np-space-3)',
                border: `1px solid ${i === 0 ? 'var(--np-border-brand)' : 'var(--np-border)'}`,
                borderRadius: 'var(--np-radius-sm)',
              }}
            >
              <div style={{ flex: 1, minWidth: 180 }}>
                <div style={{ fontWeight: 600 }}>
                  {nomeDoModelo(r)} {i === 0 && <Badge tone="brand">Mais recente</Badge>}
                </div>
                <div style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{new Date(r.created_at).toLocaleString('pt-BR')}</div>
              </div>
              <Button type="button" size="sm" variant="outline" icon={<Download size={14} />} disabled={!!baixando} onClick={() => baixar(r, 'pdf')}>
                {baixando === `${r.id}:pdf` ? 'Gerando…' : 'PDF'}
              </Button>
              <Button type="button" size="sm" variant="outline" icon={<FileText size={14} />} disabled={!!baixando} onClick={() => baixar(r, 'docx')}>
                {baixando === `${r.id}:docx` ? 'Gerando…' : 'Word'}
              </Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
