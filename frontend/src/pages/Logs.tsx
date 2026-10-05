import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listPatients } from '../api/patients'
import { listAllLogs } from '../api/reports'
import type { LogDeEdicao } from '../api/reports'
import type { Patient } from '../api/types'
import { Alert, Card, PageHeader, Select } from '../components/ds'
import styles from './Page.module.css'

const ROTULO_DO_CAMPO: Record<string, string> = {
  template_name_override: 'Modelo',
  classification_override: 'Classificação',
}

// Menu lateral → "Ver Logs": todas as edições feitas em relatórios (quem,
// quando, o que mudou), com filtro por paciente.
export default function Logs() {
  const [params, setParams] = useSearchParams()
  const pacienteId = params.get('paciente') ?? ''
  const [patients, setPatients] = useState<Patient[]>([])
  const [logs, setLogs] = useState<LogDeEdicao[] | null>(null)
  const [erro, setErro] = useState(false)

  useEffect(() => {
    listPatients()
      .then((lista) => setPatients([...lista].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))))
      .catch(() => setPatients([]))
  }, [])

  useEffect(() => {
    let ativo = true
    listAllLogs(pacienteId || undefined)
      .then((l) => ativo && setLogs(l))
      .catch(() => ativo && setErro(true))
    return () => {
      ativo = false
    }
  }, [pacienteId])

  return (
    <div>
      <PageHeader eyebrow="Registro" title="Logs De Edição" description="Todas as alterações feitas nos relatórios: quem alterou, quando e o que mudou." />
      <Card>
        <div style={{ maxWidth: 360, marginBottom: 'var(--np-space-4)' }}>
          <Select
            id="filtro-paciente-logs"
            label="Paciente"
            placeholder="Todos os pacientes"
            value={pacienteId}
            options={patients.map((p) => ({ value: p.id, label: p.name }))}
            onChange={(e) => setParams(e.target.value ? { paciente: e.target.value } : {}, { replace: true })}
          />
        </div>
        {erro && <Alert tone="danger">Não foi possível carregar os logs.</Alert>}
        {logs === null && !erro && <p>Carregando…</p>}
        {logs?.length === 0 && <p style={{ color: 'var(--np-text-muted)' }}>Nenhuma edição registrada{pacienteId ? ' para este paciente' : ''}.</p>}
        {logs && logs.length > 0 && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Paciente</th>
                  <th>Relatório</th>
                  <th>Alteração</th>
                  <th>Por</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{new Date(log.created_at).toLocaleString('pt-BR')}</td>
                    <td>
                      <Link className={styles.rowLink} to={`/pacientes/${log.patient_id}/historico`}>
                        {log.patient_name}
                      </Link>
                    </td>
                    <td>
                      {log.template_name}
                      <div style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{new Date(log.report_created_at).toLocaleDateString('pt-BR')}</div>
                    </td>
                    <td>
                      <strong>{ROTULO_DO_CAMPO[log.field] ?? log.field}:</strong> "{log.old_value ?? '(vazio)'}" → "{log.new_value ?? '(vazio)'}"
                    </td>
                    <td>{log.psychologist_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
