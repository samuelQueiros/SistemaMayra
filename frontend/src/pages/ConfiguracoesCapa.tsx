import { PageHeader } from '../components/ds'
import { EditorCapa } from '../components/EditorCapa'

export default function ConfiguracoesCapa() {
  return (
    <div>
      <PageHeader eyebrow="Configurações" title="Capa dos relatórios" description="Personalize a capa padrão e a posição do nome do paciente." />
      <EditorCapa />
    </div>
  )
}
