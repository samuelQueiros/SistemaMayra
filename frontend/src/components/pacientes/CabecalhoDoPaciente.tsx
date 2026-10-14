import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, History } from 'lucide-react'
import { getPatient } from '../../api/patients'
import type { Patient } from '../../api/types'
import { Alert, buttonClass, PageHeader } from '../ds'
import { nomeParaExibicao } from '../../utils/exibicao'

// Cabeçalho das páginas de um paciente (Formulário Dos Responsáveis, Seções
// Clínicas): carrega o paciente e oferece voltar ao histórico.
export function PaginaDoPaciente({
  patientId,
  titulo,
  descricao,
  children,
}: {
  patientId: string
  titulo: string
  descricao: string
  children: (patient: Patient) => ReactNode
}) {
  const [patient, setPatient] = useState<Patient | null>(null)
  const [erro, setErro] = useState(false)

  useEffect(() => {
    getPatient(patientId)
      .then(setPatient)
      .catch(() => setErro(true))
  }, [patientId])

  if (erro) return <Alert tone="danger">Paciente não encontrado.</Alert>
  if (!patient) return <p className="text-2">Carregando…</p>

  return (
    <div>
      <PageHeader
        eyebrow={`Pacientes · ${nomeParaExibicao(patient.name)}`}
        title={titulo}
        description={descricao}
        actions={
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
            <Link to="/pacientes" className={buttonClass('ghost')}>
              <ArrowLeft aria-hidden="true" /> Todos os pacientes
            </Link>
            <Link to={`/pacientes/${patient.id}/historico`} className={buttonClass('secondary')}>
              <History aria-hidden="true" /> Histórico
            </Link>
          </div>
        }
      />
      {children(patient)}
    </div>
  )
}
