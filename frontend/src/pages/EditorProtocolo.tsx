import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowDown, ArrowUp, Eye, Plus, Trash2 } from 'lucide-react'
import { ApiError } from '../api/client'
import { me as getMe } from '../api/auth'
import { createProtocolo, getProtocolo, updateProtocolo } from '../api/protocolos'
import { Alert, Button, Card, Checkbox, IconButton, Input, PageHeader, Select, Textarea } from '../components/ds'
import { gerarDocumento } from '../laudo/documento'
import {
  ROTULOS_TIPO_PERGUNTA,
  ROTULOS_TIPO_SECAO,
  idUnico,
  idsDoModelo,
  novaPergunta,
  novaSecao,
  novoModelo,
  opcoesPadrao,
  respostasDeExemplo,
  slug,
} from '../laudo/modelo'
import { VARIAVEIS_ESCALA, VARIAVEIS_GERAIS } from '../laudo/texto'
import type { Escala, ModeloProtocolo, Pergunta, Secao, TipoPergunta, TipoSecao } from '../laudo/tipos'

const opcoesDeTipo = <T extends string>(rotulos: Record<T, string>) =>
  (Object.keys(rotulos) as T[]).map((value) => ({ value, label: rotulos[value] }))

function mover<T>(lista: T[], de: number, para: number): T[] {
  if (para < 0 || para >= lista.length) return lista
  const copia = [...lista]
  const [item] = copia.splice(de, 1)
  copia.splice(para, 0, item)
  return copia
}

// Validações que dão para explicar melhor aqui do que a mensagem do
// servidor (que continua validando tudo).
function problemasDoModelo(modelo: ModeloProtocolo): string[] {
  const problemas: string[] = []
  if (!modelo.name.trim()) problemas.push('Dê um nome ao modelo.')
  modelo.secoes.forEach((s, i) => {
    const nome = s.titulo.trim() || `Seção ${i + 1}`
    if (!s.titulo.trim()) problemas.push(`Seção ${i + 1}: dê um título.`)
    if (s.tipo === 'perguntas') {
      if (!s.perguntas?.length) problemas.push(`${nome}: adicione pelo menos uma pergunta.`)
      s.perguntas?.forEach((p, j) => {
        if (!p.rotulo.trim()) problemas.push(`${nome}: a pergunta ${j + 1} está sem texto.`)
        if ((p.tipo === 'multipla_escolha' || p.tipo === 'caixas') && !(p.opcoes ?? []).some((o) => o.rotulo.trim()))
          problemas.push(`${nome}: a pergunta "${p.rotulo}" precisa de opções.`)
      })
    }
    if (s.tipo === 'escala' && s.escala) {
      s.escala.itens.forEach((it, j) => {
        if (!it.rotulo.trim()) problemas.push(`${nome}: o item ${j + 1} da escala está sem texto.`)
      })
      if (s.escala.opcoes.length < 2) problemas.push(`${nome}: a escala precisa de pelo menos 2 opções de resposta.`)
    }
  })
  return problemas
}

// Limpa o que o editor guarda só por conveniência (opções vazias etc.).
function paraSalvar(modelo: ModeloProtocolo): ModeloProtocolo {
  return {
    ...modelo,
    name: modelo.name.trim(),
    secoes: modelo.secoes.map((s) => ({
      ...s,
      perguntas:
        s.tipo === 'perguntas'
          ? (s.perguntas ?? []).map((p) => ({
              ...p,
              opcoes:
                p.tipo === 'multipla_escolha' || p.tipo === 'caixas' || p.tipo === 'sim_nao'
                  ? (p.opcoes ?? []).filter((o) => o.rotulo.trim())
                  : null,
            }))
          : null,
      escala: s.tipo === 'escala' ? s.escala : null,
    })),
  }
}

export default function EditorProtocolo() {
  const { id } = useParams()
  const navigate = useNavigate()
  const novo = !id || id === 'novo'
  const [modelo, setModelo] = useState<ModeloProtocolo>(novoModelo)
  // Ids já salvos não mudam (respostas e {q:id} dependem deles); os novos
  // acompanham o texto da pergunta até o primeiro salvamento.
  const [idsSalvos, setIdsSalvos] = useState<Set<string>>(new Set())
  const [carregando, setCarregando] = useState(!novo)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState<string | null>(null)
  const [previa, setPrevia] = useState<string | null>(null)
  const [gerandoPrevia, setGerandoPrevia] = useState(false)

  useEffect(() => {
    if (novo) return
    getProtocolo(id!)
      .then((p) => {
        setModelo(p.schema_json)
        setIdsSalvos(idsDoModelo(p.schema_json))
      })
      .catch((e) => setErro(e instanceof ApiError ? e.message : 'Não foi possível carregar o modelo.'))
      .finally(() => setCarregando(false))
  }, [id, novo])

  const problemas = useMemo(() => problemasDoModelo(modelo), [modelo])

  function alterarSecao(indice: number, mudanca: (s: Secao) => Secao) {
    setModelo((m) => ({ ...m, secoes: m.secoes.map((s, i) => (i === indice ? mudanca(s) : s)) }))
  }

  function renomearPergunta(indiceSecao: number, indicePergunta: number, rotulo: string) {
    setModelo((m) => {
      const pergunta = m.secoes[indiceSecao].perguntas![indicePergunta]
      let novoId = pergunta.id
      if (!idsSalvos.has(pergunta.id)) {
        const usados = idsDoModelo(m)
        usados.delete(pergunta.id)
        novoId = idUnico(slug(rotulo, 'pergunta'), usados)
      }
      const trocar = (t: string | null | undefined) =>
        novoId === pergunta.id ? t : (t ?? '').split(`{q:${pergunta.id}}`).join(`{q:${novoId}}`)
      return {
        ...m,
        secoes: m.secoes.map((s, i) => ({
          ...s,
          relatorio: { ...s.relatorio, texto_padrao: trocar(s.relatorio.texto_padrao) },
          perguntas:
            i === indiceSecao
              ? s.perguntas!.map((p, j) => (j === indicePergunta ? { ...p, rotulo, id: novoId } : p))
              : s.perguntas,
        })),
      }
    })
  }

  function adicionarSecao(tipo: TipoSecao) {
    setModelo((m) => ({ ...m, secoes: [...m.secoes, novaSecao(tipo, idsDoModelo(m))] }))
  }

  async function salvar() {
    setErro(null)
    setSucesso(null)
    if (problemas.length) {
      setErro(problemas[0])
      return
    }
    setSalvando(true)
    try {
      const dados = paraSalvar(modelo)
      const salvo = novo ? await createProtocolo(dados) : await updateProtocolo(id!, dados)
      setModelo(salvo.schema_json)
      setIdsSalvos(idsDoModelo(salvo.schema_json))
      setSucesso('Modelo salvo. Ele já aparece em Novo Atendimento.')
      if (novo) navigate(`/configuracoes/protocolos/${salvo.id}`, { replace: true })
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível salvar o modelo.')
    } finally {
      setSalvando(false)
    }
  }

  async function mostrarPrevia() {
    setGerandoPrevia(true)
    setErro(null)
    try {
      const perfil = await getMe()
      setPrevia(await gerarDocumento(modelo, respostasDeExemplo(modelo), perfil))
    } catch {
      setErro('Não foi possível montar a pré-visualização.')
    } finally {
      setGerandoPrevia(false)
    }
  }

  if (carregando) return <p>Carregando...</p>

  const todasPerguntas = modelo.secoes.flatMap((s) => s.perguntas ?? [])

  return (
    <div>
      <PageHeader
        eyebrow="Configurações · Modelos De Protocolo"
        title={novo ? 'Novo Modelo De Protocolo' : modelo.name || 'Modelo De Protocolo'}
        description="Monte as seções do formulário e o que cada uma escreve no relatório. O protocolo padrão do sistema não é alterado."
        actions={
          <div style={{ display: 'flex', gap: 'var(--np-space-3)', flexWrap: 'wrap' }}>
            <Button type="button" variant="outline" onClick={() => navigate('/configuracoes')}>
              Voltar
            </Button>
            <Button type="button" variant="outline" icon={<Eye size={16} />} onClick={mostrarPrevia} disabled={gerandoPrevia}>
              {gerandoPrevia ? 'Montando…' : 'Pré-Visualizar Relatório'}
            </Button>
            <Button type="button" onClick={salvar} disabled={salvando}>
              {salvando ? 'Salvando…' : 'Salvar Modelo'}
            </Button>
          </div>
        }
      />

      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        {erro && <Alert tone="danger">{erro}</Alert>}
        {sucesso && <Alert tone="success">{sucesso}</Alert>}

        <Card title="Dados Do Modelo">
          <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
            <Input
              id="nome-modelo"
              label="Nome Do Modelo"
              value={modelo.name}
              onChange={(e) => setModelo({ ...modelo, name: e.target.value })}
              placeholder="Ex.: Anamnese Infantil"
              required
            />
            <Textarea
              id="descricao-modelo"
              label="Descrição (Opcional)"
              rows={2}
              value={modelo.descricao ?? ''}
              onChange={(e) => setModelo({ ...modelo, descricao: e.target.value })}
              placeholder="Aparece na escolha do protocolo em Novo Atendimento."
            />
            <Textarea
              id="titulo-relatorio"
              label="Título Do Relatório"
              rows={2}
              value={modelo.titulo_relatorio}
              onChange={(e) => setModelo({ ...modelo, titulo_relatorio: e.target.value })}
              hint="Faixa cinza no topo da 1ª página do relatório. Use Enter para quebrar em duas linhas."
            />
          </div>
        </Card>

        {modelo.secoes.map((secao, i) => (
          <EditorSecao
            key={secao.id}
            numero={i + 1}
            secao={secao}
            total={modelo.secoes.length}
            todasPerguntas={todasPerguntas}
            usados={() => idsDoModelo(modelo)}
            onChange={(mudanca) => alterarSecao(i, mudanca)}
            onRenomearPergunta={(j, rotulo) => renomearPergunta(i, j, rotulo)}
            onMover={(d) => setModelo((m) => ({ ...m, secoes: mover(m.secoes, i, i + d) }))}
            onRemover={() => {
              if (modelo.secoes.length === 1) return
              if (confirm(`Remover a seção "${secao.titulo}"?`))
                setModelo((m) => ({ ...m, secoes: m.secoes.filter((_, k) => k !== i) }))
            }}
          />
        ))}

        <Card title="Adicionar Seção" subtitle="Cada seção vira uma fase do formulário e um bloco do relatório.">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
            {(Object.keys(ROTULOS_TIPO_SECAO) as TipoSecao[]).map((tipo) => (
              <Button key={tipo} type="button" variant="outline" icon={<Plus size={16} />} onClick={() => adicionarSecao(tipo)}>
                {ROTULOS_TIPO_SECAO[tipo]}
              </Button>
            ))}
          </div>
        </Card>

        {previa && (
          <Card
            title="Pré-Visualização (Respostas De Exemplo)"
            action={
              <Button type="button" variant="ghost" size="sm" onClick={() => setPrevia(null)}>
                Fechar
              </Button>
            }
          >
            <iframe
              title="Pré-visualização do relatório"
              srcDoc={previa}
              style={{ width: '100%', height: 900, border: 0, background: '#e7e7ee' }}
            />
          </Card>
        )}
      </div>
    </div>
  )
}

interface EditorSecaoProps {
  numero: number
  total: number
  secao: Secao
  todasPerguntas: Pergunta[]
  usados: () => Set<string>
  onChange: (mudanca: (s: Secao) => Secao) => void
  onRenomearPergunta: (indice: number, rotulo: string) => void
  onMover: (direcao: number) => void
  onRemover: () => void
}

function EditorSecao({ numero, total, secao, todasPerguntas, usados, onChange, onRenomearPergunta, onMover, onRemover }: EditorSecaoProps) {
  const alterarPergunta = (j: number, mudanca: Partial<Pergunta>) =>
    onChange((s) => ({ ...s, perguntas: s.perguntas!.map((p, k) => (k === j ? { ...p, ...mudanca } : p)) }))
  const alterarEscala = (mudanca: (e: Escala) => Escala) => onChange((s) => ({ ...s, escala: mudanca(s.escala!) }))
  const idTexto = `texto-padrao-${secao.id}`

  function inserirVariavel(variavel: string) {
    const el = document.getElementById(idTexto) as HTMLTextAreaElement | null
    const atual = secao.relatorio.texto_padrao ?? ''
    const inicio = el?.selectionStart ?? atual.length
    const fim = el?.selectionEnd ?? atual.length
    const novo = atual.slice(0, inicio) + variavel + atual.slice(fim)
    onChange((s) => ({ ...s, relatorio: { ...s.relatorio, texto_padrao: novo } }))
    requestAnimationFrame(() => {
      el?.focus()
      el?.setSelectionRange(inicio + variavel.length, inicio + variavel.length)
    })
  }

  return (
    <Card
      title={`${numero}. ${secao.titulo || 'Seção sem título'}`}
      subtitle={ROTULOS_TIPO_SECAO[secao.tipo]}
      action={
        <div style={{ display: 'flex', gap: 'var(--np-space-2)' }}>
          <IconButton label="Mover para cima" icon={<ArrowUp size={16} />} variant="ghost" size="sm" disabled={numero === 1} onClick={() => onMover(-1)} />
          <IconButton label="Mover para baixo" icon={<ArrowDown size={16} />} variant="ghost" size="sm" disabled={numero === total} onClick={() => onMover(1)} />
          <IconButton label="Remover seção" icon={<Trash2 size={16} />} variant="ghost" size="sm" disabled={total === 1} onClick={onRemover} />
        </div>
      }
    >
      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <Input id={`titulo-${secao.id}`} label="Título Da Seção" value={secao.titulo} onChange={(e) => onChange((s) => ({ ...s, titulo: e.target.value }))} />
        <Textarea
          id={`ajuda-${secao.id}`}
          label="Orientação Para Quem Preenche (Opcional)"
          rows={2}
          value={secao.ajuda ?? ''}
          onChange={(e) => onChange((s) => ({ ...s, ajuda: e.target.value }))}
        />

        {secao.tipo === 'perguntas' && (
          <Bloco titulo="Perguntas">
            {(secao.perguntas ?? []).map((p, j) => (
              <div key={j} style={blocoInterno}>
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr) auto', gap: 'var(--np-space-3)', alignItems: 'end' }}>
                  <Input id={`pergunta-${secao.id}-${j}`} label={`Pergunta ${j + 1}`} value={p.rotulo} onChange={(e) => onRenomearPergunta(j, e.target.value)} />
                  <Select
                    id={`tipo-${secao.id}-${j}`}
                    label="Tipo De Resposta"
                    value={p.tipo}
                    options={opcoesDeTipo(ROTULOS_TIPO_PERGUNTA)}
                    onChange={(e) => {
                      const tipo = e.target.value as TipoPergunta
                      alterarPergunta(j, { tipo, opcoes: opcoesPadrao(tipo), detalhar_quando_sim: false })
                    }}
                  />
                  <IconButton
                    label="Remover pergunta"
                    icon={<Trash2 size={16} />}
                    variant="ghost"
                    disabled={(secao.perguntas ?? []).length === 1}
                    onClick={() => onChange((s) => ({ ...s, perguntas: s.perguntas!.filter((_, k) => k !== j) }))}
                  />
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-5)' }}>
                  <Checkbox label="Essencial (avisa se ficar em branco)" checked={!!p.obrigatoria} onChange={(e) => alterarPergunta(j, { obrigatoria: e.target.checked })} />
                  {p.tipo === 'sim_nao' && (
                    <Checkbox
                      label='Pedir descrição quando a resposta for "Sim"'
                      checked={!!p.detalhar_quando_sim}
                      onChange={(e) => alterarPergunta(j, { detalhar_quando_sim: e.target.checked })}
                    />
                  )}
                </div>
                {p.opcoes && (
                  <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
                    <span style={legenda}>Opções — o texto ao lado entra no relatório quando a opção é escolhida (opcional)</span>
                    {p.opcoes.map((o, k) => (
                      <div key={k} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,2fr) auto', gap: 'var(--np-space-2)', alignItems: 'start' }}>
                        <Input
                          value={o.rotulo}
                          disabled={p.tipo === 'sim_nao'}
                          onChange={(e) => alterarPergunta(j, { opcoes: p.opcoes!.map((x, n) => (n === k ? { ...x, rotulo: e.target.value } : x)) })}
                        />
                        <Textarea
                          rows={1}
                          value={o.texto_relatorio ?? ''}
                          placeholder="Texto no relatório (opcional)"
                          onChange={(e) => alterarPergunta(j, { opcoes: p.opcoes!.map((x, n) => (n === k ? { ...x, texto_relatorio: e.target.value } : x)) })}
                        />
                        {p.tipo !== 'sim_nao' && (
                          <IconButton
                            label="Remover opção"
                            icon={<Trash2 size={14} />}
                            variant="ghost"
                            size="sm"
                            disabled={p.opcoes!.length === 1}
                            onClick={() => alterarPergunta(j, { opcoes: p.opcoes!.filter((_, n) => n !== k) })}
                          />
                        )}
                      </div>
                    ))}
                    {p.tipo !== 'sim_nao' && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        icon={<Plus size={14} />}
                        style={{ justifySelf: 'start' }}
                        onClick={() => alterarPergunta(j, { opcoes: [...p.opcoes!, { rotulo: `Opção ${p.opcoes!.length + 1}`, texto_relatorio: '' }] })}
                      >
                        Adicionar Opção
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              icon={<Plus size={14} />}
              style={{ justifySelf: 'start' }}
              onClick={() => onChange((s) => ({ ...s, perguntas: [...(s.perguntas ?? []), novaPergunta(usados())] }))}
            >
              Adicionar Pergunta
            </Button>
          </Bloco>
        )}

        {secao.tipo === 'escala' && secao.escala && (
          <EditorEscala escala={secao.escala} usados={usados} onChange={alterarEscala} />
        )}

        {secao.tipo === 'fotos' && (
          <p style={{ ...legenda, margin: 0 }}>Quem preenche anexa fotos nesta fase; elas entram no relatório nesta posição. A primeira foto também vai no cabeçalho do paciente.</p>
        )}

        <Bloco titulo="No Relatório">
          <Checkbox
            label="Mostrar esta seção no relatório"
            checked={secao.relatorio.mostrar}
            onChange={(e) => onChange((s) => ({ ...s, relatorio: { ...s.relatorio, mostrar: e.target.checked } }))}
          />
          {secao.relatorio.mostrar && (
            <>
              {(secao.tipo === 'perguntas' || secao.tipo === 'escala') && (
                <Select
                  id={`formato-${secao.id}`}
                  label="Como mostrar as respostas"
                  value={secao.relatorio.formato}
                  options={[
                    { value: 'lista', label: secao.tipo === 'escala' ? 'Tabela de itens + texto' : 'Lista (pergunta: resposta) + texto' },
                    { value: 'tabela', label: 'Tabela + texto' },
                    { value: 'so_texto', label: 'Só o texto' },
                  ]}
                  onChange={(e) => onChange((s) => ({ ...s, relatorio: { ...s.relatorio, formato: e.target.value as Secao['relatorio']['formato'] } }))}
                />
              )}
              <Textarea
                id={idTexto}
                label={secao.tipo === 'texto' ? 'Texto Inicial (editável no atendimento)' : 'Texto Padrão Do Relatório'}
                rows={5}
                value={secao.relatorio.texto_padrao ?? ''}
                onChange={(e) => onChange((s) => ({ ...s, relatorio: { ...s.relatorio, texto_padrao: e.target.value } }))}
                hint="Aparece já preenchido no atendimento e pode ser editado lá. **negrito**, ==destaque cinza==, linhas começando com • ou ✔ viram listas."
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-2)' }}>
                {[...VARIAVEIS_GERAIS, ...(secao.tipo === 'escala' ? VARIAVEIS_ESCALA : [])].map((v) => (
                  <Chip key={v.variavel} titulo={v.descricao} onClick={() => inserirVariavel(v.variavel)}>
                    {v.descricao}
                  </Chip>
                ))}
                {todasPerguntas
                  .filter((p) => p.rotulo.trim())
                  .map((p) => (
                    <Chip key={p.id} titulo={`{q:${p.id}}`} onClick={() => inserirVariavel(`{q:${p.id}}`)}>
                      Resposta: {p.rotulo.length > 40 ? p.rotulo.slice(0, 40) + '…' : p.rotulo}
                    </Chip>
                  ))}
              </div>
            </>
          )}
        </Bloco>
      </div>
    </Card>
  )
}

function EditorEscala({ escala, usados, onChange }: { escala: Escala; usados: () => Set<string>; onChange: (m: (e: Escala) => Escala) => void }) {
  return (
    <>
      <Bloco titulo="Itens Da Escala">
        {escala.itens.map((item, j) => (
          <div key={item.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto', gap: 'var(--np-space-2)', alignItems: 'end' }}>
            <Input
              id={`item-${item.id}`}
              label={`Item ${j + 1}`}
              value={item.rotulo}
              onChange={(e) => onChange((es) => ({ ...es, itens: es.itens.map((x, k) => (k === j ? { ...x, rotulo: e.target.value } : x)) }))}
            />
            <IconButton
              label="Remover item"
              icon={<Trash2 size={16} />}
              variant="ghost"
              disabled={escala.itens.length === 1}
              onClick={() => onChange((es) => ({ ...es, itens: es.itens.filter((_, k) => k !== j) }))}
            />
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          style={{ justifySelf: 'start' }}
          onClick={() => onChange((es) => ({ ...es, itens: [...es.itens, { id: idUnico(`item_${es.itens.length + 1}`, usados()), rotulo: '' }] }))}
        >
          Adicionar Item
        </Button>
      </Bloco>

      <Bloco titulo="Opções De Resposta E Pontos">
        {escala.opcoes.map((o, j) => (
          <div key={j} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr) auto', gap: 'var(--np-space-2)', alignItems: 'end' }}>
            <Input label={j === 0 ? 'Resposta' : undefined} value={o.rotulo} onChange={(e) => onChange((es) => ({ ...es, opcoes: es.opcoes.map((x, k) => (k === j ? { ...x, rotulo: e.target.value } : x)) }))} />
            <Input
              label={j === 0 ? 'Pontos' : undefined}
              type="number"
              step="any"
              value={o.valor}
              onChange={(e) => onChange((es) => ({ ...es, opcoes: es.opcoes.map((x, k) => (k === j ? { ...x, valor: Number(e.target.value) } : x)) }))}
            />
            <IconButton
              label="Remover resposta"
              icon={<Trash2 size={16} />}
              variant="ghost"
              disabled={escala.opcoes.length <= 2}
              onClick={() => onChange((es) => ({ ...es, opcoes: es.opcoes.filter((_, k) => k !== j) }))}
            />
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          style={{ justifySelf: 'start' }}
          onClick={() => onChange((es) => ({ ...es, opcoes: [...es.opcoes, { rotulo: '', valor: es.opcoes.length }] }))}
        >
          Adicionar Resposta
        </Button>
      </Bloco>

      <Bloco titulo="Classificação Pela Pontuação Total (Opcional)">
        {escala.faixas.map((f, j) => (
          <div key={j} style={blocoInterno}>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr) minmax(0,2fr) auto', gap: 'var(--np-space-2)', alignItems: 'end' }}>
              <Input label="De" type="number" step="any" value={f.min} onChange={(e) => onChange((es) => ({ ...es, faixas: es.faixas.map((x, k) => (k === j ? { ...x, min: Number(e.target.value) } : x)) }))} />
              <Input label="Até" type="number" step="any" value={f.max} onChange={(e) => onChange((es) => ({ ...es, faixas: es.faixas.map((x, k) => (k === j ? { ...x, max: Number(e.target.value) } : x)) }))} />
              <Input label="Classificação" value={f.rotulo} onChange={(e) => onChange((es) => ({ ...es, faixas: es.faixas.map((x, k) => (k === j ? { ...x, rotulo: e.target.value } : x)) }))} />
              <IconButton label="Remover faixa" icon={<Trash2 size={16} />} variant="ghost" onClick={() => onChange((es) => ({ ...es, faixas: es.faixas.filter((_, k) => k !== j) }))} />
            </div>
            <Textarea
              rows={1}
              value={f.texto_relatorio ?? ''}
              placeholder="Texto que entra no relatório nesta faixa (opcional)"
              onChange={(e) => onChange((es) => ({ ...es, faixas: es.faixas.map((x, k) => (k === j ? { ...x, texto_relatorio: e.target.value } : x)) }))}
            />
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          icon={<Plus size={14} />}
          style={{ justifySelf: 'start' }}
          onClick={() =>
            onChange((es) => {
              const inicio = es.faixas.length ? Math.max(...es.faixas.map((f) => f.max)) + 1 : 0
              return { ...es, faixas: [...es.faixas, { min: inicio, max: inicio + 5, rotulo: '', texto_relatorio: '' }] }
            })
          }
        >
          Adicionar Faixa
        </Button>
        <Checkbox
          label="Mostrar gráfico de barras no relatório"
          checked={escala.grafico === 'barras'}
          onChange={(e) => onChange((es) => ({ ...es, grafico: e.target.checked ? 'barras' : 'nenhum' }))}
        />
      </Bloco>
    </>
  )
}

const legenda = { font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' } as const
const blocoInterno = {
  display: 'grid',
  gap: 'var(--np-space-3)',
  padding: 'var(--np-space-3)',
  border: '1px solid var(--np-border)',
  borderRadius: 'var(--np-radius-sm)',
} as const

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--np-space-3)' }}>
      <legend style={{ font: 'var(--np-type-section)', marginBottom: 'var(--np-space-2)', padding: 0 }}>{titulo}</legend>
      {children}
    </fieldset>
  )
}

function Chip({ children, titulo, onClick }: { children: ReactNode; titulo: string; onClick: () => void }) {
  return (
    <button
      type="button"
      title={titulo}
      onClick={onClick}
      style={{
        border: '1px solid var(--np-border)',
        background: 'var(--np-surface-alt)',
        color: 'var(--np-text)',
        borderRadius: 999,
        padding: '2px 10px',
        font: 'var(--np-type-caption)',
        cursor: 'pointer',
      }}
    >
      + {children}
    </button>
  )
}
