import { CalendarClock, FileText, Plus, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { createPatient, listPatients } from '../api/patients'
import { getStatsSummary } from '../api/stats'
import type { Patient, StatsSummary } from '../api/types'
import { Alert, Badge, Button, buttonStyle, Card, EmptyState, Input, PageHeader, PatientAvatar, Select } from '../components/ds'
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

export default function Dashboard() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<StatsSummary | null>(null)

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [sex, setSex] = useState('')
  const [schoolInfo, setSchoolInfo] = useState('')
  const [saving, setSaving] = useState(false)

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

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await createPatient({ name, birth_date: birthDate, sex: sex || undefined, school_info: schoolInfo || undefined })
      setName('')
      setBirthDate('')
      setSex('')
      setSchoolInfo('')
      setShowForm(false)
      carregarPacientes()
    } catch {
      setError('Não foi possível cadastrar o paciente.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Painel"
        title="Pacientes"
        description="Cadastre pacientes e acompanhe o histórico de atendimentos."
        actions={
          <Button icon={<Plus size={18} />} onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancelar' : 'Novo Paciente'}
          </Button>
        }
      />

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--np-space-4)', marginBottom: 'var(--np-space-6)' }}>
          <BlocoEstatistica icon={<Users size={22} />} valor={patients.length} legenda="Pacientes cadastrados" />
          {stats && (
            <>
              <BlocoEstatistica icon={<FileText size={22} />} valor={stats.total_reports} legenda="Laudos gerados" />
              <BlocoEstatistica icon={<CalendarClock size={22} />} valor={stats.reports_last_30_days} legenda="Laudos nos últimos 30 dias" />
            </>
          )}
        </div>
      )}

      {stats && stats.reports_by_template.length > 0 && (
        <Card title="Laudos Por Escala" style={{ marginBottom: 'var(--np-space-6)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
            {stats.reports_by_template.map((item) => (
              <Badge key={item.template_name} tone="brand">
                {item.template_name}: {item.count}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {showForm && (
        <Card title="Cadastrar Paciente" style={{ marginBottom: 'var(--np-space-6)' }}>
          <form onSubmit={handleCreate} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
            <Input id="patient-name" label="Nome Completo" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input
              id="patient-birth"
              label="Data De Nascimento"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              required
            />
            <Select
              id="patient-sex"
              label="Sexo (Opcional)"
              value={sex}
              onChange={(e) => setSex(e.target.value)}
              placeholder="Não informado"
              options={[
                { value: 'Feminino', label: 'Feminino' },
                { value: 'Masculino', label: 'Masculino' },
                { value: 'Outro', label: 'Outro' },
              ]}
            />
            <Input
              id="patient-school"
              label="Escola (Opcional)"
              value={schoolInfo}
              onChange={(e) => setSchoolInfo(e.target.value)}
              placeholder="Nome da escola, ano/série, turno..."
            />
            <Button type="submit" disabled={saving} style={{ justifySelf: 'start' }}>
              {saving ? 'Salvando...' : 'Salvar Paciente'}
            </Button>
          </form>
        </Card>
      )}

      <Card title="Todos Os Pacientes">
        {error && <Alert tone="danger">{error}</Alert>}
        {loading && <p>Carregando...</p>}

        {!loading && patients.length === 0 && !error && (
          <EmptyState
            icon={<Users size={40} />}
            title="Nenhum paciente cadastrado ainda"
            description='Use o botão "Novo Paciente" acima para começar.'
          />
        )}

        {!loading && patients.length > 0 && (
          <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th></th>
                <th>Nome</th>
                <th>Data De Nascimento</th>
                <th></th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.id}>
                  <td style={{ width: 40 }}>
                    <PatientAvatar name={patient.name} size={32} />
                  </td>
                  <td>{patient.name}</td>
                  <td>{new Date(`${patient.birth_date}T00:00:00`).toLocaleDateString('pt-BR')}</td>
                  <td>
                    <Link className={styles.rowLink} to={`/pacientes/${patient.id}/historico`}>
                      Ver histórico
                    </Link>
                  </td>
                  <td>
                    <Link style={buttonStyle('outline', 'sm')} to={`/atendimento/novo?paciente=${patient.id}`}>
                      Novo Atendimento
                    </Link>
                  </td>
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
