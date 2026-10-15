import { CalendarClock, ClipboardList, ClipboardPlus, Download, Ellipsis, FileText, History, Plus, Search, Stethoscope, Trash2, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deletePatient, listPatients } from '../api/patients'
import { getStatsSummary } from '../api/stats'
import type { Patient, StatsSummary } from '../api/types'
import { Alert, Button, buttonClass, Card, EmptyState, Input, Menu, PageHeader, PatientAvatar, StatCard } from '../components/ds'
import { BaixarRelatorioDialog } from '../components/pacientes/BaixarRelatorioDialog'
import { idadeParaExibicao, nomeParaExibicao } from '../utils/exibicao'
import styles from './Page.module.css'
import { ApiError } from '../api/client'
import { NovoPacienteForm } from '../components/pacientes/NovoPacienteForm'

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
  const [novoPaciente, setNovoPaciente] = useState(false)
  const [excluir, setExcluir] = useState<Patient | null>(null)
  const [excluindo, setExcluindo] = useState(false)
  const [erroExclusao, setErroExclusao] = useState<string | null>(null)
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

  async function confirmarExclusao() {
    if (!excluir || excluindo) return
    setExcluindo(true)
    setErroExclusao(null)
    try {
      await deletePatient(excluir.id)
      setPatients((lista) => lista.filter((p) => p.id !== excluir.id))
      setExcluir(null)
      getStatsSummary().then(setStats).catch(() => setStats(null))
    } catch (e) {
      setErroExclusao(e instanceof ApiError ? e.message : 'Não foi possível excluir o paciente. Tente novamente.')
    } finally { setExcluindo(false) }
  }

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
    <div className="page-stack">
      <PageHeader
        eyebrow="Pacientes"
        title="Todos os pacientes"
        description="Cadastre pacientes e acompanhe o histórico de atendimentos."
        actions={
          <>
          <Button variant="secondary" onClick={() => setNovoPaciente(true)}>Cadastrar paciente</Button>
          <Link to="/atendimento/novo" className={buttonClass('primary', 'lg')}>
            <Plus aria-hidden="true" /> Novo atendimento
          </Link>
          </>
        }
      />

      {novoPaciente && <Card title="Cadastrar paciente"><NovoPacienteForm onCancelar={() => setNovoPaciente(false)} onCriado={(p) => {
        setPatients((lista) => [...lista, p].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')))
        setNovoPaciente(false)
      }} /></Card>}
      {!loading && (
        <div className="stat-grid">
          <StatCard icon={<Users />} tone="violeta" value={patients.length} label="Pacientes cadastrados" />
          {stats && (
            <>
              <StatCard icon={<FileText />} tone="ceu" value={stats.total_reports} label="Protocolos registrados" />
              <StatCard icon={<CalendarClock />} tone="sol" value={stats.reports_last_30_days} label="Protocolos nos últimos 30 dias" />
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
            <table className={`${styles.table} ${styles.tableStack}`}>
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
                        <div className={`${styles.rowActions} ${styles.rowActionsEnd}`}>
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
                              { label: 'Excluir paciente', icon: <Trash2 />, onSelect: () => { setErroExclusao(null); setExcluir(patient) } },
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
      {excluir && <div role="dialog" aria-modal="true" aria-label="Excluir paciente" className="dialog-backdrop">
        <Card title={`Excluir ${nomeParaExibicao(excluir.name)}?`} style={{ width: 'min(520px, 100%)' }}>
          <p>O cadastro, os relatórios, fotos, anexos e formulários deste paciente serão excluídos permanentemente. Essa ação não pode ser desfeita.</p>
          {erroExclusao && <Alert tone="danger">{erroExclusao}</Alert>}
          <div className={styles.rowActions}>
            <Button variant="secondary" disabled={excluindo} onClick={() => setExcluir(null)}>Cancelar</Button>
            <Button variant="danger" loading={excluindo} loadingLabel="Excluindo…" onClick={() => void confirmarExclusao()}>Excluir definitivamente</Button>
          </div>
        </Card>
      </div>}
      {baixarDe && <BaixarRelatorioDialog patient={baixarDe} onClose={() => setBaixarDe(null)} />}
    </div>
  )
}
