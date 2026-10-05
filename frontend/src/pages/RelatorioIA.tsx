import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listPatients } from '../api/patients'
import type { Patient } from '../api/types'
import { UserPlus } from 'lucide-react'
import { Alert, Button, Card, PageHeader, Select } from '../components/ds'
import { NovoPacienteForm } from '../components/pacientes/NovoPacienteForm'
import { EnvioDePdfsParaIA } from '../components/EnvioDePdfsParaIA'

// Menu Pacientes → "Relatório Por IA A Partir De Formulários Google":
// escolher o paciente e anexar os PDFs (o mesmo envio do Histórico).
export default function RelatorioIA() {
  const [params, setParams] = useSearchParams()
  const [patients, setPatients] = useState<Patient[] | null>(null)
  const [erro, setErro] = useState(false)
  const [cadastrando, setCadastrando] = useState(false)
  const pacienteId = params.get('paciente') ?? ''

  useEffect(() => {
    listPatients()
      .then((lista) => setPatients([...lista].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))))
      .catch(() => setErro(true))
  }, [])

  return (
    <div>
      <PageHeader
        eyebrow="Pacientes"
        title="Relatório Por IA A Partir De Formulários Google"
        description="Escolha o paciente e anexe até 6 PDFs com as respostas. A IA monta o relatório por área, com gráficos, para você revisar e exportar em PDF ou Word."
      />
      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        {erro && <Alert tone="danger">Não foi possível carregar os pacientes.</Alert>}
        <Card title="Paciente">
          {cadastrando || patients?.length === 0 ? (
            <>
              {patients?.length === 0 && (
                <p style={{ marginTop: 0, color: 'var(--np-text-muted)' }}>Nenhum paciente cadastrado ainda. Cadastre o paciente abaixo para continuar.</p>
              )}
              <NovoPacienteForm
                onCriado={(novo) => {
                  setPatients((lista) => [...(lista ?? []), novo].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR')))
                  setCadastrando(false)
                  setParams({ paciente: novo.id }, { replace: true })
                }}
                onCancelar={patients?.length ? () => setCadastrando(false) : undefined}
              />
            </>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)', alignItems: 'flex-end' }}>
              <div style={{ flex: '1 1 280px' }}>
                <Select
                  id="paciente-relatorio-ia"
                  label="Selecione O Paciente"
                  placeholder={patients === null ? 'Carregando…' : 'Selecione o paciente'}
                  value={pacienteId}
                  options={(patients ?? []).map((p) => ({ value: p.id, label: p.name }))}
                  onChange={(e) => setParams(e.target.value ? { paciente: e.target.value } : {}, { replace: true })}
                />
              </div>
              <Button type="button" variant="outline" icon={<UserPlus size={16} />} onClick={() => setCadastrando(true)} disabled={patients === null}>
                Novo Paciente
              </Button>
            </div>
          )}
        </Card>
        {pacienteId && !cadastrando && <EnvioDePdfsParaIA key={pacienteId} patientId={pacienteId} abertoInicial />}
      </div>
    </div>
  )
}
