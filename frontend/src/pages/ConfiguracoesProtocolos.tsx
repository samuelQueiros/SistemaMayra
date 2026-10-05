import { PageHeader } from '../components/ds'
import { ModelosDeProtocolo } from '../components/ModelosDeProtocolo'

export default function ConfiguracoesProtocolos() {
  return (
    <div>
      <PageHeader eyebrow="Configurações" title="Modelos De Protocolo" description="Crie e organize os modelos usados nos atendimentos." />
      <ModelosDeProtocolo />
    </div>
  )
}
