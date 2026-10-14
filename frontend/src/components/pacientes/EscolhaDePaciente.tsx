import { useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'
import { listPatients } from '../../api/patients'
import type { Patient } from '../../api/types'
import { Alert, Button, Card, Select } from '../ds'
import { NovoPacienteForm } from './NovoPacienteForm'

const porNome = (a: Patient, b: Patient) => a.name.localeCompare(b.name, 'pt-BR')

// Cartão "Paciente" das telas de IA: selecionar um paciente ou cadastrar um
// novo (sem pacientes, o cadastro já abre).
export function EscolhaDePaciente({
  id,
  pacienteId,
  onEscolher,
  onCadastrandoChange,
}: {
  id: string
  pacienteId: string
  onEscolher: (pacienteId: string) => void
  onCadastrandoChange?: (cadastrando: boolean) => void
}) {
  const [patients, setPatients] = useState<Patient[] | null>(null)
  const [erro, setErro] = useState(false)
  const [cadastrando, setCadastrandoEstado] = useState(false)

  function setCadastrando(valor: boolean) {
    setCadastrandoEstado(valor)
    onCadastrandoChange?.(valor)
  }

  useEffect(() => {
    listPatients()
      .then((lista) => setPatients([...lista].sort(porNome)))
      .catch(() => setErro(true))
  }, [])

  return (
    <>
      {erro && <Alert tone="danger">Não foi possível carregar os pacientes.</Alert>}
      <Card title="Paciente">
        {cadastrando || patients?.length === 0 ? (
          <>
            {patients?.length === 0 && (
              <p style={{ marginTop: 0, color: 'var(--np-text-muted)' }}>Nenhum paciente cadastrado ainda. Cadastre o paciente abaixo para continuar.</p>
            )}
            <NovoPacienteForm
              onCriado={(novo) => {
                setPatients((lista) => [...(lista ?? []), novo].sort(porNome))
                setCadastrando(false)
                onEscolher(novo.id)
              }}
              onCancelar={patients?.length ? () => setCadastrando(false) : undefined}
            />
          </>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)', alignItems: 'flex-end' }}>
            <div style={{ flex: '1 1 280px' }}>
              <Select
                id={id}
                label="Selecione O Paciente"
                placeholder={patients === null ? 'Carregando…' : 'Selecione o paciente'}
                value={pacienteId}
                options={(patients ?? []).map((p) => ({ value: p.id, label: p.name }))}
                onChange={(e) => onEscolher(e.target.value)}
              />
            </div>
            <Button type="button" variant="outline" icon={<UserPlus size={16} />} onClick={() => setCadastrando(true)} disabled={patients === null}>
              Novo Paciente
            </Button>
          </div>
        )}
      </Card>
    </>
  )
}
