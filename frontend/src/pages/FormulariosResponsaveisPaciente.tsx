import { useParams } from 'react-router-dom'
import { FormulariosDeResponsaveis } from '../components/pacientes/FormulariosDeResponsaveis'
import { PaginaDoPaciente } from '../components/pacientes/CabecalhoDoPaciente'

export default function FormulariosResponsaveisPaciente() {
  const { id } = useParams<{ id: string }>()
  return (
    <PaginaDoPaciente
      patientId={id!}
      titulo="Formulário dos responsáveis"
      descricao="Registre os formulários preenchidos pela família e valide cada um."
    >
      {(patient) => <FormulariosDeResponsaveis patientId={patient.id} />}
    </PaginaDoPaciente>
  )
}
