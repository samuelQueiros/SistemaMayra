import { CalendarClock, ClipboardList, ClipboardPlus, Download, Ellipsis, FileText, History, Plus, Search, Stethoscope, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPatients } from '../api/patients'
import { getStatsSummary } from '../api/stats'
import type { Patient, StatsSummary } from '../api/types'
import { Alert, buttonClass, Card, EmptyState, Input, Menu, PageHeader, PatientAvatar } from '../components/ds'
import { BaixarRelatorioDialog } from '../components/pacientes/BaixarRelatorioDialog'
import { idadeParaExibicao, nomeParaExibicao } from '../utils/exibicao'
import styles from './Page.module.css'

function BlocoEstatistica({ icon, tom, valor, legenda }: { icon: ReactNode; tom: 'violeta' | 'ceu' | 'sol'; valor: string | number; legenda: string }) {
  return (
    <Card>
      <div className="stat">
        <span className={`stat-icon stat-icon-${tom}`} aria-hidden="true">
          {icon}
        </span>
        <div>
          <span className="stat-value">{valor}</span>
          <span className="stat-label">{legenda}</span>
        </div>
      </div>
    </Card>
  )
}

const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

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

  const campoBusca = !loading && patients.length > 0 && (
    <div style={{ width: 'min(100%, 380px)' }}>
      <Input
        id="busca-pacientes"
        type="search"
        aria-label="Pesquisar pacientes"
        placeholder="Pesquisar por nome ou nascimento"
        prefix={<Search />}
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
      />
    </div>
  )

  return (
    <div>
      <PageHeader
        eyebrow="Pacientes"
        title="Todos os pacientes"
        description="Cadastre pacientes e acompanhe o histórico de atendimentos."
        actions={
          <Link to="/atendimento/novo" className={buttonClass('primary', 'lg')}>
            <Plus aria-hidden="true" /> Novo atendimento
          </Link>
        }
      />

      {!loading && (
        <div className="stat-grid">
          <BlocoEstatistica icon={<Users />} tom="violeta" valor={patients.length} legenda="Pacientes cadastrados" />
          {stats && (
            <>
              <BlocoEstatistica icon={<FileText />} tom="ceu" valor={stats.total_reports} legenda="Protocolos registrados" />
              <BlocoEstatistica icon={<CalendarClock />} tom="sol" valor={stats.reports_last_30_days} legenda="Protocolos nos últimos 30 dias" />
            </>
          )}
        </div>
      )}

      <Card title="Pacientes cadastrados" action={campoBusca}>
        {error && <Alert tone="danger">{error}</Alert>}
        {loading && <p className="text-2">Carregando…</p>}

        {!loading && patients.length === 0 && !error && (
          <EmptyState
            icon={<Users />}
            title="Nenhum paciente cadastrado ainda"
            description='Use o botão "Novo atendimento" acima para começar.'
          />
        )}

        {busca.trim() && patients.length > 0 && (
          <p className="caption" role="status" style={{ margin: '0 0 var(--s-3)' }}>
            {filtrados.length} de {patients.length} {patients.length === 1 ? 'paciente' : 'pacientes'}
          </p>
        )}

        {!loading && patients.length > 0 && filtrados.length === 0 && (
          <p className="text-2">Nenhum paciente encontrado para "{busca.trim()}".</p>
        )}

        {!loading && filtrados.length > 0 && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Paciente</th>
                  <th>Nascimento</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((patient) => {
                  const nome = nomeParaExibicao(patient.name)
                  const idade = idadeParaExibicao(patient.birth_date)
                  return (
                    <tr key={patient.id}>
                      <td>
                        <div className={styles.patientCell}>
                          <PatientAvatar name={nome} size={40} />
                          <div>
                            <span className={styles.patientName}>{nome}</span>
                            {idade && <span className={styles.patientMeta}>{idade}</span>}
                          </div>
                        </div>
                      </td>
                      <td style={{ whiteSpace: 'nowrap' }}>{new Date(`${patient.birth_date}T00:00:00`).toLocaleDateString('pt-BR')}</td>
                      <td>
                        <div className={styles.rowActions} style={{ justifyContent: 'flex-end', flexWrap: 'nowrap' }}>
                          <Link className={buttonClass('primary', 'sm')} to={`/atendimento/novo?paciente=${patient.id}`}>
                            <ClipboardPlus aria-hidden="true" /> Atendimento
                          </Link>
                          <Link className={buttonClass('secondary', 'sm')} to={`/pacientes/${patient.id}/historico`}>
                            <History aria-hidden="true" /> Histórico
                          </Link>
                          <Link className={buttonClass('secondary', 'sm')} to={`/pacientes/${patient.id}/formularios-responsaveis`}>
                            <ClipboardList aria-hidden="true" /> Responsáveis
                          </Link>
                          <Menu
                            label={`Mais ações para ${nome}`}
                            icon={<Ellipsis />}
                            items={[
                              { label: 'Seções clínicas', icon: <Stethoscope />, to: `/pacientes/${patient.id}/secoes-clinicas` },
                              { label: 'PDF / Word', icon: <Download />, onSelect: () => setBaixarDe(patient) },
                            ]}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {baixarDe && <BaixarRelatorioDialog patient={baixarDe} onClose={() => setBaixarDe(null)} />}
    </div>
  )
}
