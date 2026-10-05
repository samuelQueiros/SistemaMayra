import { CalendarClock, ClipboardList, ClipboardPlus, Download, FileText, History, Plus, Search, Stethoscope, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPatients } from '../api/patients'
import { getStatsSummary } from '../api/stats'
import type { Patient, StatsSummary } from '../api/types'
import { Alert, Button, buttonStyle, Card, EmptyState, Input, PageHeader, PatientAvatar } from '../components/ds'
import { BaixarRelatorioDialog } from '../components/pacientes/BaixarRelatorioDialog'
import styles from './Page.module.css'

function BlocoEstatistica({ icon, valor, legenda }: { icon: React.ReactNode; valor: string | number; legenda: string }) {
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--np-space-3)' }}>
        <span
          style={{
            width: 44,
            height: 44,
            borderRadius: 'var(--np-radius-md)',
            background: 'var(--np-purple-100)',
            color: 'var(--np-primary)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: '0 0 auto',
          }}
        >
          {icon}
        </span>
        <div>
          <span style={{ display: 'block', font: 'var(--np-type-display)', fontSize: 'var(--np-text-2xl)', color: 'var(--np-text)' }}>{valor}</span>
          <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-subtle)' }}>{legenda}</span>
        </div>
      </div>
    </Card>
  )
}

const semAcento = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

// Busca por nome (sem diferenciar acentos/maiúsculas) ou pela data de
// nascimento como aparece na tela (ex.: 15/03 ou 2018).
function filtrarPacientes(patients: Patient[], busca: string): Patient[] {
  const termo = semAcento(busca.trim())
  if (!termo) return patients
  return patients.filter((p) => {
    const nascimento = new Date(`${p.birth_date}T00:00:00`).toLocaleDateString('pt-BR')
    return semAcento(p.name).includes(termo) || nascimento.includes(termo)
  })
}

export default function Dashboard() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<StatsSummary | null>(null)
  const [baixarDe, setBaixarDe] = useState<Patient | null>(null)
  const [busca, setBusca] = useState('')
  const filtrados = useMemo(() => filtrarPacientes(patients, busca), [patients, busca])

  function carregarPacientes() {
    setLoading(true)
    listPatients()
      .then(setPatients)
      .catch(() => setError('Não foi possível carregar os pacientes.'))
      .finally(() => setLoading(false))
  }

  useEffect(carregarPacientes, [])

  useEffect(() => {
    getStatsSummary()
      .then(setStats)
      .catch(() => setStats(null))
  }, [])

  return (
    <div>
      <PageHeader
        eyebrow="Pacientes"
        title="Todos Os Pacientes"
        description="Cadastre pacientes e acompanhe o histórico de atendimentos."
        actions={
          <Link to="/atendimento/novo" style={buttonStyle('primary')}>
            <Plus size={18} /> Novo Atendimento
          </Link>
        }
      />

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--np-space-4)', marginBottom: 'var(--np-space-6)' }}>
          <BlocoEstatistica icon={<Users size={22} />} valor={patients.length} legenda="Pacientes cadastrados" />
          {stats && (
            <>
              <BlocoEstatistica icon={<FileText size={22} />} valor={stats.total_reports} legenda="Protocolos registrados" />
              <BlocoEstatistica icon={<CalendarClock size={22} />} valor={stats.reports_last_30_days} legenda="Protocolos nos últimos 30 dias" />
            </>
          )}
        </div>
      )}

      <Card title="Pacientes Cadastrados">
        {error && <Alert tone="danger">{error}</Alert>}
        {loading && <p>Carregando...</p>}

        {!loading && patients.length === 0 && !error && (
          <EmptyState
            icon={<Users size={40} />}
            title="Nenhum paciente cadastrado ainda"
            description='Use o botão "Novo Atendimento" acima para começar.'
          />
        )}

        {!loading && patients.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)', alignItems: 'center', marginBottom: 'var(--np-space-4)' }}>
            <div style={{ flex: '1 1 320px', maxWidth: 480 }}>
              <Input
                id="busca-pacientes"
                type="search"
                placeholder="Pesquisar por nome ou data de nascimento"
                prefix={<Search size={16} />}
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
              />
            </div>
            {busca.trim() && (
              <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>
                {filtrados.length} de {patients.length} {patients.length === 1 ? 'paciente' : 'pacientes'}
              </span>
            )}
          </div>
        )}

        {!loading && patients.length > 0 && filtrados.length === 0 && (
          <p style={{ color: 'var(--np-text-muted)' }}>Nenhum paciente encontrado para "{busca.trim()}".</p>
        )}

        {!loading && filtrados.length > 0 && (
          <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th></th>
                <th>Nome</th>
                <th>Data De Nascimento</th>
                <th>Opções</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((patient) => (
                <tr key={patient.id}>
                  <td style={{ width: 40 }}>
                    <PatientAvatar name={patient.name} size={32} />
                  </td>
                  <td>{patient.name}</td>
                  <td>{new Date(`${patient.birth_date}T00:00:00`).toLocaleDateString('pt-BR')}</td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-2)', alignItems: 'center' }}>
                      <Link style={buttonStyle('primary', 'sm')} to={`/atendimento/novo?paciente=${patient.id}`}>
                        <ClipboardPlus size={14} /> Novo Atendimento
                      </Link>
                      <Link style={buttonStyle('outline', 'sm')} to={`/pacientes/${patient.id}/historico`}>
                        <History size={14} /> Histórico
                      </Link>
                      <Link style={buttonStyle('outline', 'sm')} to={`/pacientes/${patient.id}/formularios-responsaveis`}>
                        <ClipboardList size={14} /> Formulário Dos Responsáveis
                      </Link>
                      <Link style={buttonStyle('outline', 'sm')} to={`/pacientes/${patient.id}/secoes-clinicas`}>
                        <Stethoscope size={14} /> Seções Clínicas
                      </Link>
                      <Button type="button" variant="outline" size="sm" icon={<Download size={14} />} onClick={() => setBaixarDe(patient)}>
                        PDF / Word
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Card>
      {baixarDe && <BaixarRelatorioDialog patient={baixarDe} onClose={() => setBaixarDe(null)} />}
    </div>
  )
}
