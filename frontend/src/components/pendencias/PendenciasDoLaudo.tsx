import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronDown, ChevronRight, Ellipsis, Plus, Undo2 } from 'lucide-react'
import { ApiError } from '../../api/client'
import type { CatalogoDoProtocolo } from '../../api/laudoIA'
import {
  enviarCatalogoDoLaudo,
  getPendencias,
  marcarEscalasAplicadas,
  salvarDadosComplementares,
} from '../../api/pendencias'
import type {
  CampoDaPendencia,
  DadoComplementar,
  GrupoPendente,
  ItemPendente,
  PendenciasDoLaudo as Pendencias,
  Situacao,
  Valor,
} from '../../api/pendencias'
import { Alert, Badge, Button, Input, Menu, ProgressBar, SaveStatus, SectionBand, Select } from '../ds'
import { rotuloParaExibicao } from '../../utils/exibicao'

// Espera depois da última alteração antes de salvar (salvamento automático).
const ESPERA_DO_SALVAMENTO_MS = 800

const DISPENSAS: Record<Exclude<Situacao, 'preenchido'>, string> = {
  nao_se_aplica: 'Não se aplica',
  nao_informado: 'Não informado pela família',
}

export interface EstadoDasPendencias {
  alterado: boolean
  salvando: boolean
  estudoEditado: boolean
}

// Alterações locais por campo: undefined = sem alteração; null = apagado.
type Locais = Record<string, DadoComplementar | null>

interface Props {
  laudoId: string
  pacienteId: string
  /** Catálogo do formulário, para laudos antigos que não guardaram uma cópia. */
  obterCatalogo: () => Promise<CatalogoDoProtocolo>
  /** Conteúdo abaixo da lista (ex.: botão "Atualizar laudo"). */
  children?: (estado: EstadoDasPendencias) => ReactNode
  /** Área por seção (ex.: anexar foto); recebe a chave e o título da seção. */
  acoesDaSecao?: (grupo: GrupoPendente) => ReactNode
  /** Acima da lista (ex.: anexar foto geral). */
  topo?: ReactNode
  /** Incrementado por quem usa o componente para recarregar (ex.: sugestões novas). */
  recarregar?: number
}

const horaAgora = () => new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

function rotuloDaOpcao(o: { valor: string; rotulo: string }) {
  if (!o.rotulo || o.rotulo === o.valor) return o.valor
  // CARS: o rótulo é a descrição clínica longa do grau.
  return o.rotulo.length > 70 ? `${o.valor} — ${o.rotulo.slice(0, 67)}…` : o.rotulo
}

export function PendenciasDoLaudo({ laudoId, pacienteId, obterCatalogo, children, acoesDaSecao, topo, recarregar = 0 }: Props) {
  const [pendencias, setPendencias] = useState<Pendencias | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [locais, setLocais] = useState<Locais>({})
  const [status, setStatus] = useState('')
  const [abertos, setAbertos] = useState<Record<string, boolean>>({})
  const fila = useRef<Locais>({})
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [alterado, setAlterado] = useState(false)

  const carregar = useCallback(async () => {
    try {
      setPendencias(await getPendencias(laudoId))
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPendencias(await enviarCatalogoDoLaudo(laudoId, await obterCatalogo()))
      } else throw e
    }
  }, [laudoId, obterCatalogo])

  useEffect(() => {
    carregar().catch(() => setErro('Não foi possível carregar o que falta preencher.'))
  }, [carregar, recarregar])

  const salvar = useCallback(async () => {
    temporizador.current = null
    const lote = fila.current
    if (!Object.keys(lote).length) return
    fila.current = {}
    setStatus('Salvando…')
    try {
      await salvarDadosComplementares(pacienteId, lote)
      setStatus(`Salvo às ${horaAgora()}`)
    } catch {
      fila.current = { ...lote, ...fila.current }
      setStatus('Alterações ainda não salvas — tente de novo em instantes.')
    }
  }, [pacienteId])

  // Ao sair da tela com algo na fila, salva na hora.
  useEffect(
    () => () => {
      if (temporizador.current) {
        clearTimeout(temporizador.current)
        void salvar()
      }
    },
    [salvar],
  )

  function alterar(mudancas: Locais) {
    setAlterado(true)
    setLocais((atual) => ({ ...atual, ...mudancas }))
    fila.current = { ...fila.current, ...mudancas }
    setStatus('Alterações ainda não salvas')
    if (temporizador.current) clearTimeout(temporizador.current)
    temporizador.current = setTimeout(() => void salvar(), ESPERA_DO_SALVAMENTO_MS)
  }

  // Estado atual (servidor + alterações locais).
  function valorDe(item: ItemPendente, campoId: string): Valor {
    const local = locais[campoId]
    if (local !== undefined) return local?.valor ?? null
    return item.valores[campoId] ?? null
  }
  function situacaoDe(item: ItemPendente): Situacao | null {
    const local = locais[item.chave]
    if (local !== undefined) return local?.situacao ?? null
    return item.situacao
  }

  function preencher(campo: CampoDaPendencia, valor: Valor, extra: Partial<DadoComplementar> = {}) {
    const vazio = valor === null || valor === ''
    alterar({ [campo.id]: vazio ? null : { valor, situacao: 'preenchido', origem: 'digitado', ...extra } })
  }

  async function adicionarEscala(chave: string) {
    if (!pendencias) return
    const aplicadas = pendencias.grupos.filter((g) => g.escala).map((g) => g.chave.replace(/^escala_/, ''))
    try {
      setPendencias(await marcarEscalasAplicadas(laudoId, [...aplicadas, chave]))
    } catch {
      setErro('Não foi possível incluir a escala.')
    }
  }

  if (erro && !pendencias) return <Alert tone="danger">{erro}</Alert>
  if (!pendencias) return <p style={{ color: 'var(--text-2)' }}>Verificando o que faltou…</p>

  // Progresso com as alterações locais (cada escala conta 1).
  let total = 0
  let resolvidos = 0
  for (const g of pendencias.grupos) {
    if (!g.essencial) continue
    const essenciais = g.itens.filter((i) => i.essencial)
    if (g.escala) {
      total += 1
      resolvidos += essenciais.every((i) => situacaoDe(i)) ? 1 : 0
    } else {
      total += essenciais.length
      resolvidos += essenciais.filter((i) => situacaoDe(i)).length
    }
  }
  const essenciais = pendencias.grupos.filter((g) => g.essencial)
  const opcionais = pendencias.grupos.filter((g) => !g.essencial)
  const alternar = (chave: string) => setAbertos((a) => ({ ...a, [chave]: !a[chave] }))

  function campo(item: ItemPendente, c: CampoDaPendencia, rotulo: string) {
    const valor = valorDe(item, c.id)
    const id = `pend-${c.id}`
    if (c.tipo === 'simnao') {
      return (
        <div role="group" aria-label={rotulo} style={{ display: 'flex', gap: 'var(--s-2)' }}>
          {['Sim', 'Não'].map((opcao) => (
            <Button
              key={opcao}
              type="button"
              size="sm"
              variant={valor === opcao ? 'primary' : 'secondary'}
              aria-pressed={valor === opcao}
              onClick={() => preencher(c, valor === opcao ? null : opcao)}
            >
              {opcao}
            </Button>
          ))}
        </div>
      )
    }
    if (c.tipo === 'opcao') {
      return (
        <Select
          id={id}
          aria-label={rotulo}
          value={typeof valor === 'string' ? valor : ''}
          options={c.opcoes.map((o) => ({ value: o.valor, label: rotuloDaOpcao(o) }))}
          onChange={(e) => preencher(c, e.target.value)}
        />
      )
    }
    return (
      <Input
        id={id}
        aria-label={rotulo}
        type={c.tipo === 'numero' ? 'number' : c.tipo === 'data' ? 'date' : 'text'}
        min={c.min ?? undefined}
        max={c.max ?? undefined}
        value={valor === null || typeof valor === 'boolean' ? '' : valor}
        onChange={(e) => preencher(c, c.tipo === 'numero' && e.target.value !== '' ? Number(e.target.value) : e.target.value)}
      />
    )
  }

  function linha(item: ItemPendente) {
    const rotulo = rotuloParaExibicao(item.rotulo)
    const situacao = situacaoDe(item)
    const dispensado = situacao === 'nao_se_aplica' || situacao === 'nao_informado'
    const sugestoes = item.sugestoes.filter((s) => locais[s.campo_id] === undefined)
    return (
      <div key={item.chave} className="pendencia-item" style={{ display: 'grid', gap: 'var(--s-2)', padding: 'var(--s-3) 0', borderTop: '1px solid var(--divider)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-3)' }}>
          <span style={{ flex: '1 1 220px', color: dispensado ? 'var(--text-2)' : 'var(--text)' }}>
            {rotulo}
            {item.essencial && !dispensado && <span aria-hidden="true" style={{ color: 'var(--danger)' }}> *</span>}
          </span>
          {dispensado ? (
            <>
              <Badge tone="neutral">{DISPENSAS[situacao]}</Badge>
              <Button type="button" size="sm" variant="ghost" icon={<Undo2 />} onClick={() => alterar({ [item.chave]: null })}>
                Desfazer
              </Button>
            </>
          ) : (
            <>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)', flex: '2 1 260px' }}>
                {item.campos.map((c) => (
                  <div key={c.id} style={{ flex: '1 1 140px' }}>
                    {campo(item, c, rotulo)}
                  </div>
                ))}
              </div>
              {situacao === 'preenchido' && <Badge tone="success">Preenchido</Badge>}
              <Menu
                label={`Mais opções para ${rotulo}`}
                icon={<Ellipsis />}
                size="sm"
                items={(Object.keys(DISPENSAS) as (keyof typeof DISPENSAS)[]).map((s) => ({
                  label: DISPENSAS[s],
                  onSelect: () => alterar(Object.fromEntries(item.campos.map((c, i) => [c.id, i === 0 ? { situacao: s, valor: null } : null]))),
                }))}
              />
            </>
          )}
        </div>
        {!dispensado &&
          sugestoes.map((s) => {
            const alvo = item.campos.find((c) => c.id === s.campo_id) ?? item.campos[0]
            const opcao = alvo.opcoes.find((o) => o.valor === s.valor)
            return (
              <div
                key={`${s.anexo_id}-${s.campo_id}`}
                className="pendencia-sugestao"
                style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2)', padding: 'var(--s-2) var(--s-3)', background: 'var(--sol-50)', border: '1px solid var(--sol-300)', borderRadius: 'var(--r-sm)' }}
              >
                <span style={{ flex: '1 1 240px' }}>
                  Sugestão da foto <strong>“{s.anexo_nome}”</strong>: {opcao ? rotuloDaOpcao(opcao) : s.valor}
                  {s.trecho && <span style={{ color: 'var(--text-2)' }}> — “{s.trecho}”</span>}
                </span>
                <Button type="button" size="sm" onClick={() => preencher(alvo, s.valor, { origem: 'anexo', anexo_id: s.anexo_id })}>
                  Confirmar
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    preencher(alvo, s.valor, { origem: 'anexo', anexo_id: s.anexo_id })
                    document.getElementById(`pend-${alvo.id}`)?.focus()
                  }}
                >
                  Corrigir
                </Button>
              </div>
            )
          })}
      </div>
    )
  }

  function grupo(g: GrupoPendente, numero: number) {
    const aberto = abertos[g.chave] ?? !g.escala
    const visiveis = g.escala ? g.itens : g.itens.filter((i) => i.essencial || !g.essencial)
    const extras = g.escala ? [] : g.itens.filter((i) => !i.essencial && g.essencial)
    const pendentes = (g.essencial ? g.itens.filter((i) => i.essencial) : g.itens).filter((i) => !situacaoDe(i)).length
    const meta = g.escala ? `${pendentes} ${pendentes === 1 ? 'item sem resposta' : 'itens sem resposta'}` : `${pendentes} ${pendentes === 1 ? 'pendente' : 'pendentes'}`
    return (
      <section key={g.chave} aria-label={g.titulo} style={{ display: 'grid', gap: 'var(--s-2)' }}>
        <SectionBand number={numero} title={g.titulo} meta={meta} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' }}>
          {g.escala && (
            <Button type="button" size="sm" variant="tonal" icon={aberto ? <ChevronDown /> : <ChevronRight />} onClick={() => alternar(g.chave)} aria-expanded={aberto}>
              {aberto ? 'Fechar a escala' : 'Preencher'}
            </Button>
          )}
          {acoesDaSecao?.(g)}
        </div>
        {aberto && <div>{visiveis.map(linha)}</div>}
        {extras.length > 0 && (
          <>
            <Button type="button" size="sm" variant="ghost" icon={abertos[`${g.chave}:extras`] ? <ChevronDown /> : <ChevronRight />} onClick={() => alternar(`${g.chave}:extras`)} aria-expanded={!!abertos[`${g.chave}:extras`]}>
              {abertos[`${g.chave}:extras`] ? 'Ocultar opcionais' : `Mais ${extras.length} opcionais`}
            </Button>
            {abertos[`${g.chave}:extras`] && <div>{extras.map(linha)}</div>}
          </>
        )}
      </section>
    )
  }

  // Algo ainda não chegou ao servidor (esperando o envio ou enviando).
  const salvando = status !== '' && !status.startsWith('Salvo')
  return (
    <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--s-3)' }}>
        <h3 style={{ margin: 0, font: 'var(--type-h3)' }}>Dados que faltaram</h3>
        {status && <SaveStatus status={status} salvo={false} />}
      </div>
      {pendencias.grupos.length === 0 ? (
        <Alert tone="success">Os PDFs trouxeram tudo o que o protocolo pede.</Alert>
      ) : (
        <>
          {total > 0 && (
            <ProgressBar value={resolvidos} max={total} caption={`${resolvidos} de ${total} essenciais preenchidos`} />
          )}
          {topo}
          {essenciais.map((g, i) => grupo(g, i + 1))}
          {pendencias.escalas_para_adicionar.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2)' }}>
              <span style={{ color: 'var(--text-2)' }}>Também apliquei:</span>
              {pendencias.escalas_para_adicionar.map((e) => (
                <Button key={e.chave} type="button" size="sm" variant="secondary" icon={<Plus />} onClick={() => adicionarEscala(e.chave)}>
                  {e.titulo}
                </Button>
              ))}
            </div>
          )}
          {opcionais.length > 0 && (
            <div>
              <Button type="button" variant="ghost" icon={abertos.__opcionais ? <ChevronDown /> : <ChevronRight />} onClick={() => alternar('__opcionais')} aria-expanded={!!abertos.__opcionais}>
                Opcionais ({opcionais.reduce((n, g) => n + g.itens.length, 0)})
              </Button>
              {abertos.__opcionais && <div style={{ display: 'grid', gap: 'var(--s-5)', marginTop: 'var(--s-3)' }}>{opcionais.map((g, i) => grupo(g, essenciais.length + i + 1))}</div>}
            </div>
          )}
        </>
      )}
      {erro && <Alert tone="danger">{erro}</Alert>}
      {children?.({ alterado, salvando, estudoEditado: !!pendencias.estudo_de_caso?.editado })}
    </div>
  )
}
