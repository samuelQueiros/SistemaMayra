import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Check, Download, Eye, FileText, Save } from 'lucide-react'
import { ApiError, downloadBlob } from '../api/client'
import { me as getMe } from '../api/auth'
import { createPatient, getPatient } from '../api/patients'
import {
  createLaudoProtocolo,
  getLaudoProtocolo,
  getProtocolo,
  salvarDocumentoLaudo,
  salvarRespostasLaudo,
} from '../api/protocolos'
import type { Psychologist } from '../api/types'
import { Alert, Button, Card, Checkbox, Input, PageHeader, ProgressBar, Select, Textarea } from '../components/ds'
import { gerarDocumento, textoDaSecao } from '../laudo/documento'
import { CAPA_CONFIG_SISTEMA, arquivoParaDataUri, prepararCapaA4 } from '../laudo/imagens'
import { essenciaisEmBranco, respostasVazias, secaoPreenchida } from '../laudo/modelo'
import { pontuarEscala } from '../laudo/texto'
import type { ModeloProtocolo, Pergunta, RespostasProtocolo, Secao } from '../laudo/tipos'

const ATRASO_AUTOSAVE_MS = 1200

const nomeArquivo = (nome: string) => 'Relatorio_' + (nome.trim() || 'Paciente').replace(/[^a-zA-Z0-9À-ÿ]+/g, '_')

export default function AtendimentoProtocolo() {
  const { modeloId } = useParams()
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const laudoParam = params.get('laudo')
  const pacienteParam = params.get('paciente')

  const [modelo, setModelo] = useState<ModeloProtocolo | null>(null)
  const [r, setR] = useState<RespostasProtocolo>(() => respostasVazias())
  const [pacienteId, setPacienteId] = useState<string | null>(pacienteParam)
  const [laudoId, setLaudoId] = useState<string | null>(laudoParam)
  const [perfil, setPerfil] = useState<Psychologist | null>(null)
  const [fase, setFase] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [previa, setPrevia] = useState<string | null>(null)
  const pendente = useRef(false)
  const temporizador = useRef<number | undefined>(undefined)

  useEffect(() => {
    let ativo = true
    async function carregar() {
      try {
        setPerfil(await getMe())
        if (laudoParam) {
          const laudo = await getLaudoProtocolo(laudoParam)
          const copia = laudo.computed_json?.modelo
          if (!ativo) return
          setModelo(copia ?? (await getProtocolo(modeloId!)).schema_json)
          setR({ ...respostasVazias(), ...laudo.answers_json })
          setPacienteId(laudo.patient_id)
          return
        }
        const p = await getProtocolo(modeloId!)
        if (!ativo) return
        setModelo(p.schema_json)
        if (pacienteParam) {
          const paciente = await getPatient(pacienteParam)
          if (!ativo) return
          setR(respostasVazias({ nome: paciente.name, data_nascimento: paciente.birth_date, sexo: paciente.sex ?? '' }))
        }
      } catch (e) {
        setErro(e instanceof ApiError ? e.message : 'Não foi possível abrir o protocolo.')
      }
    }
    carregar()
    return () => {
      ativo = false
    }
  }, [modeloId, laudoParam, pacienteParam])

  // Aviso ao sair com alterações ainda não gravadas no sistema.
  useEffect(() => {
    function antesDeSair(e: BeforeUnloadEvent) {
      if (!pendente.current) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', antesDeSair)
    return () => window.removeEventListener('beforeunload', antesDeSair)
  }, [])

  const salvarRespostas = useCallback(
    async (dados: RespostasProtocolo) => {
      if (!laudoId) return
      setStatus('Salvando alterações…')
      try {
        await salvarRespostasLaudo(laudoId, dados)
        pendente.current = false
        setStatus(`✓ Alterações salvas às ${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`)
      } catch (e) {
        setStatus('Alterações ainda não salvas: ' + (e instanceof ApiError ? e.message : 'erro de conexão.'))
      }
    },
    [laudoId],
  )

  // Toda alteração passa por aqui: atualiza a tela e agenda o autosave.
  const alterar = useCallback(
    (mudanca: (atual: RespostasProtocolo) => RespostasProtocolo) => {
      setR((atual) => {
        const novo = mudanca(atual)
        pendente.current = true
        window.clearTimeout(temporizador.current)
        if (laudoId) temporizador.current = window.setTimeout(() => salvarRespostas(novo), ATRASO_AUTOSAVE_MS)
        return novo
      })
    },
    [laudoId, salvarRespostas],
  )

  const fases = useMemo(() => (modelo ? ['Identificação', ...modelo.secoes.map((s) => s.titulo), 'Relatório'] : []), [modelo])

  if (erro && !modelo) return <Alert tone="danger">{erro}</Alert>
  if (!modelo || !perfil) return <p>Carregando…</p>

  const concluidas = modelo.secoes.filter((s) => secaoPreenchida(s, r)).length
  const identificacaoOk = !!r.identificacao.nome.trim() && !!r.identificacao.data_nascimento

  async function documento(): Promise<string> {
    return gerarDocumento(modelo!, r, perfil!)
  }

  async function salvarNoSistema(): Promise<{ laudo: string; paciente: string } | null> {
    setErro(null)
    if (!identificacaoOk) {
      setFase(0)
      setErro('Preencha o nome e a data de nascimento do paciente antes de salvar.')
      return null
    }
    setOcupado('salvar')
    try {
      let idPaciente = pacienteId
      if (!idPaciente) {
        const novo = await createPatient({
          name: r.identificacao.nome.trim(),
          birth_date: r.identificacao.data_nascimento,
          sex: r.identificacao.sexo || undefined,
        })
        idPaciente = novo.id
        setPacienteId(novo.id)
      }
      let id = laudoId
      if (!id) {
        const laudo = await createLaudoProtocolo(idPaciente, modeloId!, r)
        id = laudo.id
        setLaudoId(id)
        setParams({ laudo: id }, { replace: true })
      } else {
        await salvarRespostasLaudo(id, r)
      }
      await salvarDocumentoLaudo(id, await documento())
      pendente.current = false
      setStatus(`✓ Protocolo e relatório salvos no sistema às ${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`)
      return { laudo: id, paciente: idPaciente }
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível salvar no sistema.')
      return null
    } finally {
      setOcupado(null)
    }
  }

  async function exportar(formato: 'pdf' | 'docx') {
    setErro(null)
    setOcupado(formato)
    try {
      const nome = nomeArquivo(r.identificacao.nome)
      await downloadBlob(`/documents/${formato}`, { html: await documento(), file_name: nome }, `${nome}.${formato}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : `Não foi possível gerar o ${formato === 'pdf' ? 'PDF' : 'Word'}.`)
    } finally {
      setOcupado(null)
    }
  }

  async function preVisualizar() {
    setOcupado('previa')
    try {
      setPrevia(await documento())
    } catch {
      setErro('Não foi possível montar a pré-visualização.')
    } finally {
      setOcupado(null)
    }
  }

  async function concluir() {
    const salvo = await salvarNoSistema()
    if (salvo) navigate(`/pacientes/${salvo.paciente}/historico`)
  }

  function irPara(i: number) {
    const atual = fase >= 1 && fase <= modelo!.secoes.length ? modelo!.secoes[fase - 1] : null
    const faltando = atual ? essenciaisEmBranco(atual, r) : []
    setAviso(faltando.length && i > fase ? `Ficaram em branco: ${faltando.map((p) => p.rotulo).join('; ')}.` : null)
    setFase(i)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const secaoAtual = fase >= 1 && fase <= modelo.secoes.length ? modelo.secoes[fase - 1] : null

  return (
    <div>
      <PageHeader
        eyebrow="Atendimento"
        title={modelo.name}
        description={laudoId ? 'Alterações são salvas automaticamente no sistema.' : 'Preencha e clique em "Salvar Laudo" para registrar o paciente e o protocolo.'}
        meta={status ? <span style={{ font: 'var(--np-type-caption)' }}>{status}</span> : undefined}
      />

      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <ProgressBar value={concluidas} max={modelo.secoes.length} label={`${concluidas} de ${modelo.secoes.length} seções preenchidas`} />
        <nav aria-label="Fases do protocolo" style={{ display: 'flex', gap: 'var(--np-space-2)', overflowX: 'auto', paddingBottom: 4 }}>
          {fases.map((nome, i) => {
            const secao = i >= 1 && i <= modelo.secoes.length ? modelo.secoes[i - 1] : null
            const ok = i === 0 ? identificacaoOk : secao ? secaoPreenchida(secao, r) : false
            return (
              <button
                key={i}
                type="button"
                onClick={() => irPara(i)}
                aria-current={i === fase ? 'step' : undefined}
                style={{
                  flex: '0 0 auto',
                  border: `1px solid ${i === fase ? 'var(--np-primary)' : 'var(--np-border)'}`,
                  background: i === fase ? 'var(--np-primary)' : 'var(--np-surface)',
                  color: i === fase ? '#fff' : 'var(--np-text)',
                  borderRadius: 999,
                  padding: '4px 12px',
                  cursor: 'pointer',
                  font: 'var(--np-type-caption)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                {ok && <Check size={12} />} {i + 1}. {nome}
              </button>
            )
          })}
        </nav>

        {erro && <Alert tone="danger">{erro}</Alert>}
        {aviso && <Alert tone="warning">{aviso}</Alert>}

        {fase === 0 && <FaseIdentificacao r={r} alterar={alterar} pacienteExistente={!!pacienteId} />}
        {secaoAtual && <FaseSecao key={secaoAtual.id} secao={secaoAtual} modelo={modelo} r={r} alterar={alterar} />}
        {fase === fases.length - 1 && (
          <FaseRelatorio
            r={r}
            perfil={perfil}
            alterar={alterar}
            ocupado={ocupado}
            onPrevia={preVisualizar}
            onExportar={exportar}
            previa={previa}
          />
        )}

        <div
          style={{
            position: 'sticky',
            bottom: 0,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--np-space-3)',
            padding: 'var(--np-space-3) 0',
            background: 'var(--np-bg, var(--np-surface))',
            borderTop: '1px solid var(--np-border)',
          }}
        >
          <Button type="button" variant="outline" disabled={fase === 0} onClick={() => irPara(fase - 1)}>
            Fase Anterior
          </Button>
          <Button type="button" variant="outline" disabled={fase === fases.length - 1} onClick={() => irPara(fase + 1)}>
            Próxima Fase
          </Button>
          <span style={{ flex: 1 }} />
          <Button type="button" icon={<Save size={16} />} onClick={salvarNoSistema} disabled={!!ocupado}>
            {ocupado === 'salvar' ? 'Salvando…' : laudoId ? 'Atualizar Laudo' : 'Salvar Laudo'}
          </Button>
          {laudoId && (
            <Button type="button" variant="secondary" onClick={concluir} disabled={!!ocupado}>
              Concluir E Ver Histórico
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

type Alterar = (mudanca: (atual: RespostasProtocolo) => RespostasProtocolo) => void

function FaseIdentificacao({ r, alterar, pacienteExistente }: { r: RespostasProtocolo; alterar: Alterar; pacienteExistente: boolean }) {
  const id = r.identificacao
  const set = (campo: keyof typeof id) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    alterar((a) => ({ ...a, identificacao: { ...a.identificacao, [campo]: e.target.value } }))
  return (
    <Card title="Identificação" subtitle={pacienteExistente ? 'Paciente já cadastrado — dados vindos do cadastro.' : 'O paciente é cadastrado ao salvar no sistema.'}>
      <div style={{ display: 'grid', gap: 'var(--np-space-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
        <Input id="id-nome" label="Nome Do Paciente" value={id.nome} onChange={set('nome')} required disabled={pacienteExistente} />
        <Input id="id-nascimento" label="Data De Nascimento" type="date" value={id.data_nascimento} onChange={set('data_nascimento')} required disabled={pacienteExistente} />
        <Select
          id="id-sexo"
          label="Sexo"
          value={id.sexo}
          placeholder="Selecione"
          options={[
            { value: 'Feminino', label: 'Feminino' },
            { value: 'Masculino', label: 'Masculino' },
          ]}
          onChange={set('sexo')}
        />
        <Input id="id-responsavel" label="Responsável" value={id.responsavel} onChange={set('responsavel')} />
        <Input id="id-cidade" label="Cidade (Assinatura)" value={id.cidade} onChange={set('cidade')} placeholder="Ex.: Gama – DF" />
        <Input id="id-data" label="Data Do Relatório" type="date" value={id.data_relatorio} onChange={set('data_relatorio')} />
      </div>
    </Card>
  )
}

function FaseSecao({ secao, modelo, r, alterar }: { secao: Secao; modelo: ModeloProtocolo; r: RespostasProtocolo; alterar: Alterar }) {
  const resultado = secao.escala ? pontuarEscala(secao.escala, r.escalas[secao.id]) : null
  const salvo = r.textos[secao.id]
  const texto = textoDaSecao(secao, modelo, r)
  const mostrarTexto = secao.relatorio.mostrar || secao.tipo === 'texto'

  async function adicionarFotos(e: ChangeEvent<HTMLInputElement>) {
    const arquivos = Array.from(e.target.files ?? []).filter((a) => a.type.startsWith('image/'))
    e.target.value = ''
    const novas = await Promise.all(arquivos.map(async (a) => ({ nome: a.name, src: await arquivoParaDataUri(a) })))
    alterar((a) => ({ ...a, fotos: { ...a.fotos, [secao.id]: [...(a.fotos[secao.id] ?? []), ...novas] } }))
  }

  return (
    <Card title={secao.titulo} subtitle={secao.ajuda || undefined}>
      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        {(secao.perguntas ?? []).map((p) => (
          <CampoPergunta key={p.id} pergunta={p} r={r} alterar={alterar} />
        ))}

        {secao.escala && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={celula}>Item</th>
                  {secao.escala.opcoes.map((o, k) => (
                    <th key={k} style={{ ...celula, textAlign: 'center' }}>
                      {o.rotulo}
                      <div style={{ fontWeight: 400, font: 'var(--np-type-caption)' }}>{o.valor} pt</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {secao.escala.itens.map((item) => (
                  <tr key={item.id}>
                    <td style={celula}>{item.rotulo}</td>
                    {secao.escala!.opcoes.map((o, k) => (
                      <td key={k} style={{ ...celula, textAlign: 'center' }}>
                        <input
                          type="radio"
                          name={`${secao.id}-${item.id}`}
                          aria-label={`${item.rotulo}: ${o.rotulo}`}
                          checked={r.escalas[secao.id]?.[item.id] === k}
                          onChange={() =>
                            alterar((a) => ({ ...a, escalas: { ...a.escalas, [secao.id]: { ...(a.escalas[secao.id] ?? {}), [item.id]: k } } }))
                          }
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {resultado && (
              <p style={{ margin: 'var(--np-space-3) 0 0' }}>
                <strong>Pontuação:</strong> {resultado.pontuacao} de {resultado.maxima} ({resultado.respondidos} de {secao.escala.itens.length} itens)
                {resultado.faixa && (
                  <>
                    {' '}
                    · <strong>Classificação:</strong> {resultado.faixa.rotulo}
                  </>
                )}
              </p>
            )}
          </div>
        )}

        {secao.tipo === 'fotos' && (
          <div style={{ display: 'grid', gap: 'var(--np-space-3)' }}>
            <input type="file" accept="image/*" multiple onChange={adicionarFotos} aria-label="Adicionar fotos" />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
              {(r.fotos[secao.id] ?? []).map((f, i) => (
                <div key={i} style={{ display: 'grid', gap: 4, justifyItems: 'start' }}>
                  <img src={f.src} alt={`Foto ${i + 1}`} style={{ width: 150, height: 110, objectFit: 'cover', borderRadius: 6 }} />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => alterar((a) => ({ ...a, fotos: { ...a.fotos, [secao.id]: (a.fotos[secao.id] ?? []).filter((_, k) => k !== i) } }))}
                  >
                    Remover
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {mostrarTexto && (
          <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
            <Textarea
              id={`texto-${secao.id}`}
              label={secao.tipo === 'texto' ? 'Texto' : 'Texto Do Relatório'}
              rows={6}
              value={texto}
              onChange={(e) => alterar((a) => ({ ...a, textos: { ...a.textos, [secao.id]: { valor: e.target.value, editado: true } } }))}
              hint={
                salvo?.editado
                  ? 'Texto editado por você — não muda mais com as respostas.'
                  : 'Montado automaticamente pelas respostas. Pode editar à vontade.'
              }
            />
            {salvo?.editado && secao.tipo !== 'texto' && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                style={{ justifySelf: 'start' }}
                onClick={() => {
                  if (confirm('Voltar ao texto automático? O que você escreveu nesta seção será substituído.'))
                    alterar((a) => {
                      const textos = { ...a.textos }
                      delete textos[secao.id]
                      return { ...a, textos }
                    })
                }}
              >
                Voltar Ao Texto Automático
              </Button>
            )}
          </div>
        )}
        {!secao.relatorio.mostrar && <p style={{ margin: 0, font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>Esta seção é de uso interno: não aparece no relatório.</p>}
      </div>
    </Card>
  )
}

const celula = { border: '1px solid var(--np-border)', padding: '6px 8px', textAlign: 'left' } as const

function Rotulo({ pergunta, children }: { pergunta: Pergunta; children: ReactNode }) {
  return (
    <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
      <span style={{ fontWeight: 600 }}>
        {pergunta.rotulo}
        {pergunta.obrigatoria && <span style={{ color: 'var(--np-danger, #c0392b)' }}> *</span>}
      </span>
      {pergunta.ajuda && <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{pergunta.ajuda}</span>}
      {children}
    </div>
  )
}

function CampoPergunta({ pergunta: p, r, alterar }: { pergunta: Pergunta; r: RespostasProtocolo; alterar: Alterar }) {
  const valor = r.respostas[p.id]
  const definir = (v: string | string[]) => alterar((a) => ({ ...a, respostas: { ...a.respostas, [p.id]: v } }))
  const texto = typeof valor === 'string' ? valor : ''

  if (p.tipo === 'texto_longo') {
    return (
      <Rotulo pergunta={p}>
        <Textarea id={`q-${p.id}`} rows={4} value={texto} onChange={(e) => definir(e.target.value)} />
      </Rotulo>
    )
  }
  if (p.tipo === 'sim_nao' || p.tipo === 'multipla_escolha') {
    const opcoes = p.tipo === 'sim_nao' ? ['Sim', 'Não'] : (p.opcoes ?? []).map((o) => o.rotulo)
    return (
      <Rotulo pergunta={p}>
        <div role="radiogroup" aria-label={p.rotulo} style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-2)' }}>
          {opcoes.map((o) => (
            <Button key={o} type="button" size="sm" variant={texto === o ? 'primary' : 'outline'} aria-pressed={texto === o} onClick={() => definir(texto === o ? '' : o)}>
              {o}
            </Button>
          ))}
        </div>
        {p.tipo === 'sim_nao' && p.detalhar_quando_sim && texto === 'Sim' && (
          <Input
            id={`q-${p.id}-detalhe`}
            label="Descreva"
            value={r.detalhes[p.id] ?? ''}
            onChange={(e) => alterar((a) => ({ ...a, detalhes: { ...a.detalhes, [p.id]: e.target.value } }))}
          />
        )}
      </Rotulo>
    )
  }
  if (p.tipo === 'caixas') {
    const marcadas = Array.isArray(valor) ? valor : []
    return (
      <Rotulo pergunta={p}>
        <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
          {(p.opcoes ?? []).map((o) => (
            <Checkbox
              key={o.rotulo}
              label={o.rotulo}
              checked={marcadas.includes(o.rotulo)}
              onChange={(e) => definir(e.target.checked ? [...marcadas, o.rotulo] : marcadas.filter((m) => m !== o.rotulo))}
            />
          ))}
        </div>
      </Rotulo>
    )
  }
  return (
    <Rotulo pergunta={p}>
      <Input
        id={`q-${p.id}`}
        type={p.tipo === 'data' ? 'date' : p.tipo === 'numero' ? 'number' : 'text'}
        step={p.tipo === 'numero' ? 'any' : undefined}
        value={texto}
        onChange={(e) => definir(e.target.value)}
      />
    </Rotulo>
  )
}

function FaseRelatorio({
  r,
  perfil,
  alterar,
  ocupado,
  onPrevia,
  onExportar,
  previa,
}: {
  r: RespostasProtocolo
  perfil: Psychologist
  alterar: Alterar
  ocupado: string | null
  onPrevia: () => void
  onExportar: (f: 'pdf' | 'docx') => void
  previa: string | null
}) {
  async function trocarCapa(e: ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0]
    e.target.value = ''
    if (!arquivo) return
    const { src } = await prepararCapaA4(arquivo)
    const config = perfil.capa_config ?? (perfil.tem_capa_personalizada ? { ...CAPA_CONFIG_SISTEMA, escreverNome: false } : CAPA_CONFIG_SISTEMA)
    alterar((a) => ({ ...a, capa: { src, config } }))
  }

  return (
    <>
      <Card title="Capa Deste Relatório (Opcional)" subtitle="Por padrão usa a capa de Configurações. Envie outra imagem (A4 em pé) só se este relatório precisar de uma capa diferente.">
        <div style={{ display: 'grid', gap: 'var(--np-space-3)' }}>
          <input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={trocarCapa} aria-label="Enviar capa deste relatório" />
          {r.capa && (
            <div style={{ display: 'flex', gap: 'var(--np-space-4)', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <img src={r.capa.src} alt="Capa deste relatório" style={{ width: 140, border: '1px solid var(--np-border)', borderRadius: 4 }} />
              <div style={{ display: 'grid', gap: 'var(--np-space-3)' }}>
                <Checkbox
                  label="Escrever o nome do paciente na capa (mesma posição da capa de Configurações)"
                  checked={r.capa.config.escreverNome}
                  onChange={(e) => alterar((a) => ({ ...a, capa: a.capa && { ...a.capa, config: { ...a.capa.config, escreverNome: e.target.checked } } }))}
                />
                <Button type="button" variant="outline" size="sm" style={{ justifySelf: 'start' }} onClick={() => alterar((a) => ({ ...a, capa: null }))}>
                  Usar A Capa Padrão
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>

      <Card title="Relatório">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
          <Button type="button" variant="outline" icon={<Eye size={16} />} onClick={onPrevia} disabled={!!ocupado}>
            {ocupado === 'previa' ? 'Montando…' : 'Pré-Visualizar'}
          </Button>
          <Button type="button" variant="outline" icon={<Download size={16} />} onClick={() => onExportar('pdf')} disabled={!!ocupado}>
            {ocupado === 'pdf' ? 'Gerando PDF…' : 'Gerar PDF'}
          </Button>
          <Button type="button" variant="outline" icon={<FileText size={16} />} onClick={() => onExportar('docx')} disabled={!!ocupado}>
            {ocupado === 'docx' ? 'Gerando Word…' : 'Gerar Word'}
          </Button>
        </div>
        {previa && (
          <iframe
            title="Pré-visualização do relatório"
            sandbox="" srcDoc={previa}
            style={{ width: '100%', height: 1000, border: 0, background: '#e7e7ee', marginTop: 'var(--np-space-4)' }}
          />
        )}
        <p style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)', marginBottom: 0 }}>
          Para mudar a capa padrão, os dados da assinatura ou o texto "Sobre a profissional", vá em <Link to="/configuracoes/capa">Configurações</Link>.
        </p>
      </Card>
    </>
  )
}
