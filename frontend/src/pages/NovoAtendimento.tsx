import { useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/ds'

export default function NovoAtendimento() {
  const [params] = useSearchParams()
  const pacienteId = params.get('paciente')
  const src = pacienteId
    ? `/formulario-novo-paciente.html?paciente=${pacienteId}`
    : '/formulario-novo-paciente.html'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <PageHeader
        eyebrow="Atendimento"
        title="Novo Atendimento"
        description="Preencha o protocolo completo. Ao salvar, o paciente e o protocolo ficam registrados no histórico."
      />
      <iframe
        key={src}
        src={src}
        title="Formulário De Avaliação"
        style={{
          flex: 1,
          minHeight: '80vh',
          width: '100%',
          border: '1px solid var(--np-border)',
          borderRadius: 'var(--np-radius-md)',
          background: '#fff',
        }}
      />
    </div>
  )
}
