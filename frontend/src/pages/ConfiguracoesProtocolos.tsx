/** Configurações > Protocolos: página que hospeda a lista de modelos de protocolo próprios. */
import { PageHeader } from '../components/ds'
import { ModelosDeProtocolo } from '../components/ModelosDeProtocolo'

export default function ConfiguracoesProtocolos() {
  return (
    <div>
      <PageHeader eyebrow="Configurações" title="Modelos de protocolo" description="Crie e organize os modelos usados nos atendimentos." />
      <ModelosDeProtocolo />
    </div>
  )
}
