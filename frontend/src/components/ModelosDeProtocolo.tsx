import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Copy, Pencil, Plus } from 'lucide-react'
import { ApiError } from '../api/client'
import { arquivarProtocolo, duplicarProtocolo, listProtocolos, restaurarProtocolo } from '../api/protocolos'
import type { Protocolo } from '../laudo/tipos'
import { Alert, Badge, Button, Card, buttonStyle } from './ds'

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
      title="Modelos De Protocolo"
      subtitle="Formulários próprios, além do protocolo padrão. Em Novo Atendimento você escolhe qual usar; cada um gera o relatório no mesmo padrão visual."
      action={
        <Link to="/configuracoes/protocolos/novo" style={buttonStyle('primary', 'sm')}>
          <Plus size={16} /> Novo Modelo
        </Link>
      }
    >
      <div style={{ display: 'grid', gap: 'var(--np-space-3)' }}>
        {erro && <Alert tone="danger">{erro}</Alert>}
        <Linha
          titulo="Avaliação Neuropsicopedagógica E Análise Comportamental"
          detalhe="Protocolo padrão do sistema — não editável."
          etiqueta={<Badge tone="neutral">Padrão</Badge>}
        />
        {modelos === null && !erro && <p style={{ margin: 0 }}>Carregando…</p>}
        {ativos.map((m) => (
          <Linha
            key={m.id}
            titulo={m.name}
            detalhe={`${m.schema_json.secoes.length} ${m.schema_json.secoes.length === 1 ? 'seção' : 'seções'}${m.schema_json.descricao ? ' · ' + m.schema_json.descricao : ''}`}
            acoes={
              <>
                <Link to={`/configuracoes/protocolos/${m.id}`} style={buttonStyle('outline', 'sm')}>
                  <Pencil size={14} /> Editar
                </Link>
                <Button type="button" variant="ghost" size="sm" icon={<Copy size={14} />} onClick={() => executar(() => duplicarProtocolo(m.id), false)}>
                  Duplicar
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Arquivar o modelo "${m.name}"? Ele some de Novo Atendimento, mas os relatórios já feitos continuam no histórico.`))
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
          <p style={{ margin: 0, color: 'var(--np-text-muted)' }}>Nenhum modelo próprio ainda. Clique em "Novo Modelo" para montar o primeiro.</p>
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
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 'var(--np-space-3)',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--np-space-3) var(--np-space-4)',
        border: '1px solid var(--np-border)',
        borderRadius: 'var(--np-radius-sm)',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>
          {titulo} {etiqueta}
        </div>
        <div style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{detalhe}</div>
      </div>
      {acoes && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-2)' }}>{acoes}</div>}
    </div>
  )
}
