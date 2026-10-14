import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Copy, Pencil, Plus } from 'lucide-react'
import { ApiError } from '../api/client'
import { arquivarProtocolo, duplicarProtocolo, listProtocolos, restaurarProtocolo } from '../api/protocolos'
import type { Protocolo } from '../laudo/tipos'
import { Alert, Badge, Button, Card, buttonClass } from './ds'

// Card de Configurações: modelos de protocolo da psicóloga. O protocolo
// padrão (formulario-novo-paciente.html) aparece só como referência.
export function ModelosDeProtocolo() {
  const [modelos, setModelos] = useState<Protocolo[] | null>(null)
  const [mostrarArquivados, setMostrarArquivados] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    listProtocolos(true)
      .then(setModelos)
      .catch(() => setErro('Não foi possível carregar os modelos de protocolo.'))
  }, [])

  async function executar(acao: () => Promise<Protocolo>, substituir: boolean) {
    setErro(null)
    try {
      const resultado = await acao()
      setModelos((lista) =>
        substituir
          ? (lista ?? []).map((m) => (m.id === resultado.id ? resultado : m))
          : [...(lista ?? []), resultado].sort((a, b) => a.name.localeCompare(b.name)),
      )
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível concluir a ação.')
    }
  }

  const ativos = (modelos ?? []).filter((m) => !m.arquivado)
  const arquivados = (modelos ?? []).filter((m) => m.arquivado)

  return (
    <Card
      title="Modelos de protocolo"
      subtitle="Formulários próprios, além do protocolo padrão. Em “Novo atendimento” você escolhe qual usar; cada um gera o relatório no mesmo padrão visual."
      action={
        <Link to="/configuracoes/protocolos/novo" className={buttonClass('primary', 'sm')}>
          <Plus aria-hidden="true" /> Novo modelo
        </Link>
      }
    >
      <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
        {erro && <Alert tone="danger">{erro}</Alert>}
        <Linha
          titulo="Avaliação neuropsicopedagógica e análise comportamental"
          detalhe="Protocolo padrão do sistema — não editável."
          etiqueta={<Badge tone="neutral">Padrão</Badge>}
        />
        {modelos === null && !erro && <p className="text-2" style={{ margin: 0 }}>Carregando…</p>}
        {ativos.map((m) => (
          <Linha
            key={m.id}
            titulo={m.name}
            detalhe={`${m.schema_json.secoes.length} ${m.schema_json.secoes.length === 1 ? 'seção' : 'seções'}${m.schema_json.descricao ? ' · ' + m.schema_json.descricao : ''}`}
            acoes={
              <>
                <Link to={`/configuracoes/protocolos/${m.id}`} className={buttonClass('secondary', 'sm')}>
                  <Pencil aria-hidden="true" /> Editar
                </Link>
                <Button type="button" variant="ghost" size="sm" icon={<Copy />} onClick={() => executar(() => duplicarProtocolo(m.id), false)}>
                  Duplicar
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Arquivar o modelo "${m.name}"? Ele some de “Novo atendimento”, mas os relatórios já feitos continuam no histórico.`))
                      executar(() => arquivarProtocolo(m.id), true)
                  }}
                >
                  Arquivar
                </Button>
              </>
            }
          />
        ))}
        {modelos !== null && !ativos.length && (
          <p className="text-2" style={{ margin: 0 }}>Nenhum modelo próprio ainda. Clique em "Novo modelo" para montar o primeiro.</p>
        )}
        {arquivados.length > 0 && (
          <Button type="button" variant="ghost" size="sm" style={{ justifySelf: 'start' }} onClick={() => setMostrarArquivados((v) => !v)}>
            {mostrarArquivados ? 'Esconder' : 'Mostrar'} arquivados ({arquivados.length})
          </Button>
        )}
        {mostrarArquivados &&
          arquivados.map((m) => (
            <Linha
              key={m.id}
              titulo={m.name}
              detalhe="Arquivado"
              acoes={
                <Button type="button" variant="ghost" size="sm" onClick={() => executar(() => restaurarProtocolo(m.id), true)}>
                  Restaurar
                </Button>
              }
            />
          ))}
      </div>
    </Card>
  )
}

function Linha({ titulo, detalhe, etiqueta, acoes }: { titulo: string; detalhe: string; etiqueta?: React.ReactNode; acoes?: React.ReactNode }) {
  return (
    <div className="list-row">
      <div style={{ minWidth: 0 }}>
        <div className="list-row-title">
          {titulo} {etiqueta}
        </div>
        <div className="list-row-meta">{detalhe}</div>
      </div>
      {acoes && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' }}>{acoes}</div>}
    </div>
  )
}
