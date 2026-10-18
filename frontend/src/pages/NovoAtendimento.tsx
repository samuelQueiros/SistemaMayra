import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleCheck, CircleDashed, ClipboardList } from 'lucide-react'
import { listProtocolos } from '../api/protocolos'
import { Badge, Card, PageHeader } from '../components/ds'
import type { Protocolo } from '../laudo/tipos'

const MENSAGEM_SAIDA =
  'Há alterações no protocolo que ainda não foram salvas no sistema.\n\nSair mesmo assim?'

// Novo Atendimento: se a psicóloga tem modelos de protocolo próprios
// (Configurações), primeiro pergunta qual usar; senão (ou escolhido o
// padrão), abre direto o protocolo padrão, como sempre.
export default function NovoAtendimento() {
  const [params] = useSearchParams()
  const pacienteId = params.get('paciente')
  const escolhido = params.get('protocolo')
  const laudoId = params.get('laudo')
  const [modelos, setModelos] = useState<Protocolo[] | null>(escolhido || laudoId ? [] : null)

  useEffect(() => {
    if (escolhido || laudoId) return
    listProtocolos()
      .then(setModelos)
      .catch(() => setModelos([]))
  }, [escolhido, laudoId])

  if (laudoId) return <ProtocoloPadrao pacienteId={null} laudoId={laudoId} />
  if (modelos === null) return <p className="text-2">Carregando…</p>
  if (escolhido === 'padrao' || !modelos.length) return <ProtocoloPadrao pacienteId={pacienteId} />

  const sufixoPaciente = pacienteId ? `paciente=${pacienteId}` : ''
  return (
    <div>
      <PageHeader eyebrow="Atendimento" title="Novo atendimento" description="Qual protocolo você vai usar neste atendimento?" />
      <div style={{ display: 'grid', gap: 'var(--s-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 320px), 1fr))' }}>
        <CartaoProtocolo
          para={`/atendimento/novo?protocolo=padrao${sufixoPaciente ? '&' + sufixoPaciente : ''}`}
          titulo="Avaliação neuropsicopedagógica e análise comportamental"
          descricao="Protocolo padrão do sistema (CARS, ATA, SNAP-IV, Portage e demais fases)."
        />
        {modelos.map((m) => (
          <CartaoProtocolo
            key={m.id}
            para={`/atendimento/protocolo/${m.id}${sufixoPaciente ? '?' + sufixoPaciente : ''}`}
            titulo={m.name}
            descricao={m.schema_json.descricao || `${m.schema_json.secoes.length} seções`}
          />
        ))}
      </div>
    </div>
  )
}

function CartaoProtocolo({ para, titulo, descricao }: { para: string; titulo: string; descricao: string }) {
  return (
    <Link to={para} className="card-link">
      <Card>
        <div className="protocolo-card">
          <span className="stat-icon stat-icon-violeta" aria-hidden="true">
            <ClipboardList />
          </span>
          <div className="protocolo-card-texto">
            <div className="protocolo-card-titulo">{titulo}</div>
            <div className="caption">{descricao}</div>
          </div>
        </div>
      </Card>
    </Link>
  )
}

type Salvamento = { estado: 'nao-salvo' } | { estado: 'salvo'; hora: string | null }

// Etiqueta do cabeçalho: lê o aviso de alterações pendentes que o
// formulário (iframe) já manda para a janela pai.
function EtiquetaDeSalvamento({ salvamento }: { salvamento: Salvamento }) {
  if (salvamento.estado === 'nao-salvo') {
    return (
      <Badge tone="warning" icon={<CircleDashed aria-hidden="true" />}>
        Ainda não salvo
      </Badge>
    )
  }
  return (
    <Badge tone="success" icon={<CircleCheck aria-hidden="true" />}>
      {salvamento.hora ? `Salvo às ${salvamento.hora}` : 'Laudo salvo'}
    </Badge>
  )
}

// Protocolo padrão (formulario-novo-paciente.html) embutido num iframe —
// comportamento de sempre. Com `laudoId`, reabre um laudo já salvo (ex.:
// gerado pelo Relatório por IA) para ajustes.
function ProtocoloPadrao({ pacienteId, laudoId = null }: { pacienteId: string | null; laudoId?: string | null }) {
  const src = laudoId
    ? `/formulario-novo-paciente.html?laudo=${laudoId}`
    : pacienteId
      ? `/formulario-novo-paciente.html?paciente=${pacienteId}`
      : '/formulario-novo-paciente.html'

  // O formulário (iframe) avisa quando há alterações ainda não gravadas no
  // banco. Enquanto houver, fechar/recarregar a aba ou sair pelo menu pede
  // confirmação — o iframe sozinho não consegue impedir a troca de rota.
  const alteracoesPendentes = useRef(false)
  const [salvamento, setSalvamento] = useState<Salvamento>(laudoId ? { estado: 'salvo', hora: null } : { estado: 'nao-salvo' })

  useEffect(() => {
    alteracoesPendentes.current = false

    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return
      const dados = event.data as { tipo?: string; pendente?: boolean } | null
      if (dados?.tipo === 'protocolo:alteracoes-pendentes') {
        alteracoesPendentes.current = Boolean(dados.pendente)
        setSalvamento(
          dados.pendente
            ? { estado: 'nao-salvo' }
            : { estado: 'salvo', hora: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) },
        )
      }
    }

    function onBeforeUnload(event: BeforeUnloadEvent) {
      if (!alteracoesPendentes.current) return
      event.preventDefault()
      event.returnValue = ''
    }

    function onClickCaptura(event: MouseEvent) {
      if (!alteracoesPendentes.current) return
      const alvo = event.target as Element | null
      const saida = alvo?.closest('a[href]:not([target="_blank"]), [data-confirmar-saida]')
      if (!saida) return
      if (window.confirm(MENSAGEM_SAIDA)) {
        alteracoesPendentes.current = false
        return
      }
      event.preventDefault()
      event.stopPropagation()
    }

    window.addEventListener('message', onMessage)
    window.addEventListener('beforeunload', onBeforeUnload)
    document.addEventListener('click', onClickCaptura, true)
    return () => {
      window.removeEventListener('message', onMessage)
      window.removeEventListener('beforeunload', onBeforeUnload)
      document.removeEventListener('click', onClickCaptura, true)
    }
  }, [src])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <PageHeader
        eyebrow="Atendimento"
        title={laudoId ? 'Ajustar laudo' : 'Novo atendimento'}
        description={
          laudoId
            ? 'Revise e ajuste o protocolo deste laudo. As alterações são salvas automaticamente; clique em "Atualizar Relatório" para atualizar o documento.'
            : 'Preencha o protocolo completo. Ao salvar, o paciente e o protocolo ficam registrados no histórico.'
        }
        actions={<EtiquetaDeSalvamento salvamento={salvamento} />}
      />
      <iframe
        key={src}
        src={src}
        title="Formulário de avaliação"
        style={{ flex: 1, minHeight: '80vh', width: '100%', display: 'block', border: 0, background: 'transparent' }}
      />
    </div>
  )
}
