import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { listReports } from '../api/reports'
import { listTemplates } from '../api/templates'
import type { ReportResumo, ReportTemplate } from '../api/types'
import { Alert, Card, Select } from '../components/ds'
import { PaginaDoPaciente } from '../components/pacientes/CabecalhoDoPaciente'
import { SecoesClinicasForm } from '../components/pacientes/SecoesClinicasForm'

// Seções clínicas são por relatório: a página lista os relatórios do
// paciente (mais recente primeiro) e edita as seções do escolhido.
export default function SecoesClinicasPaciente() {
  const { id } = useParams<{ id: string }>()
  const [params, setParams] = useSearchParams()
  const [reports, setReports] = useState<ReportResumo[] | null>(null)
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listReports(id!), listTemplates()])
      .then(([r, t]) => {
        setReports([...r].sort((a, b) => b.created_at.localeCompare(a.created_at)))
        setTemplates(t)
      })
      .catch(() => setErro('Não foi possível carregar os relatórios deste paciente.'))
  }, [id])

  const nomeDoModelo = (r: ReportResumo) => r.template_name_override ?? templates.find((t) => t.id === r.template_id)?.name ?? 'Relatório'
  const escolhido = reports?.find((r) => r.id === params.get('relatorio')) ?? reports?.[0]

  return (
    <PaginaDoPaciente
      patientId={id!}
      titulo="Seções Clínicas"
      descricao="Anamnese, hipóteses diagnósticas, encaminhamentos e conduta — registradas em cada relatório."
    >
      {() => (
        <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
          {erro && <Alert tone="danger">{erro}</Alert>}
          {reports === null && !erro && <p>Carregando…</p>}
          {reports?.length === 0 && (
            <Card>
              <p style={{ margin: 0, color: 'var(--np-text-muted)' }}>
                Este paciente ainda não tem relatórios. As seções clínicas são registradas em um relatório — faça um novo atendimento primeiro.
              </p>
            </Card>
          )}
          {reports && reports.length > 0 && escolhido && (
            <>
              <Card>
                <Select
                  id="relatorio-secoes"
                  label="Relatório"
                  value={escolhido.id}
                  options={reports.map((r, i) => ({
                    value: r.id,
                    label: `${new Date(r.created_at).toLocaleDateString('pt-BR')} — ${nomeDoModelo(r)}${i === 0 ? ' (mais recente)' : ''}`,
                  }))}
                  onChange={(e) => setParams({ relatorio: e.target.value }, { replace: true })}
                />
              </Card>
              <SecoesClinicasForm
                key={escolhido.id}
                report={escolhido}
                onSaved={(atualizado) => setReports((lista) => (lista ?? []).map((r) => (r.id === atualizado.id ? atualizado : r)))}
              />
            </>
          )}
        </div>
      )}
    </PaginaDoPaciente>
  )
}
