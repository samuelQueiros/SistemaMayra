import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Download, FileText, PencilLine, Plus, Sparkles } from 'lucide-react'
import { ApiError } from '../api/client'
import { MAXIMO_DE_PDFS_LAUDO, acompanharGeracao, gerarLaudoPorIA, problemaNosPdfsDoLaudo } from '../api/laudoIA'
import { atualizarLaudo } from '../api/pendencias'
import type { PendenciasDoLaudo } from '../api/pendencias'
import { carregarPendencias } from '../api/carregarPendencias'
import type { AndamentoDoLaudoIA, CatalogoDoProtocolo, LaudoPorIA as Laudo } from '../api/laudoIA'
import { downloadReportDocx, downloadReportPdf, getReport, getReportResumo } from '../api/reports'
import { Alert, Button, buttonClass, Card, Input, Select, PageHeader, Textarea } from '../components/ds'
import { EscolhaDePaciente } from '../components/pacientes/EscolhaDePaciente'
import { SeletorDePdfs } from '../components/SeletorDePdfs'
import { CamposQueFaltam } from '../components/pendencias/CamposQueFaltam'

type Etapa = 'preencher' | 'catalogo' | 'ia' | 'documento' | 'pronto'

const MENSAGEM_DA_ETAPA: Record<Etapa, string> = {
  preencher: '',
  catalogo: 'Preparando o protocolo do paciente…',
  ia: 'Enviando os PDFs…',
  documento: 'Gerando o laudo padrão com os gráficos…',
  pronto: '',
}

const SITUACAO_DO_DOCUMENTO: Record<AndamentoDoLaudoIA['documentos'][number]['status'], string> = {
  aguardando: 'aguardando',
  lendo: 'lendo…',
  lido: 'lido ✓',
  erro: 'não foi possível ler',
}

interface MensagemDoFormulario {
  tipo: string
  catalogo?: CatalogoDoProtocolo
  mensagem?: string
}

// Menu Pacientes → "Relatório por IA": a psicóloga envia os PDFs (Google Forms e
// escalas), a IA escreve o estudo de caso e preenche o protocolo padrão, e o
// próprio formulário (num iframe oculto) gera o laudo oficial com os
// gráficos. Fluxo separado do preenchimento manual.
export default function LaudoPorIA() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const pacienteId = params.get('paciente') ?? ''
  // Aberto pelo Histórico ("Completar dados") para um laudo já gerado.
  const laudoDoHistorico = params.get('laudo')
  const [cadastrando, setCadastrando] = useState(false)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [dataRelatorio, setDataRelatorio] = useState('')
  const [cidade, setCidade] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const [etapa, setEtapa] = useState<Etapa>('preencher')
  const [erro, setErro] = useState<string | null>(null)
  const [andamento, setAndamento] = useState<AndamentoDoLaudoIA | null>(null)
  // "Atualizar laudo" (dados que faltaram): andamento, resultado e recarga das pendências.
  const [atualizando, setAtualizando] = useState<string | null>(null)
  const [resultadoDaAtualizacao, setResultadoDaAtualizacao] = useState<{ tom: 'success' | 'danger'; texto: string } | null>(null)
  const [recarregarPendencias, setRecarregarPendencias] = useState(0)
  const [laudo, setLaudo] = useState<Laudo | null>(null)
  // Pendências carregadas junto com o resumo: o modal abre direto, sem outra espera.
  const [pendenciasIniciais, setPendenciasIniciais] = useState<PendenciasDoLaudo | null>(null)
  const [carregandoPrevia, setCarregandoPrevia] = useState(false)
  const [erroAbertura, setErroAbertura] = useState<string | null>(null)
  const [laudoSemDocumento, setLaudoSemDocumento] = useState<string | null>(null)
  const [iframeSrc, setIframeSrc] = useState<string | null>(null)
  const espera = useRef<{ tipo: string; resolver: (m: MensagemDoFormulario) => void; rejeitar: (e: Error) => void } | null>(null)

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return
      const dados = event.data as MensagemDoFormulario | null
      const atual = espera.current
      if (!atual || !dados?.tipo?.startsWith('laudo-ia:')) return
      if (dados.tipo === 'laudo-ia:erro') atual.rejeitar(new Error(dados.mensagem || 'O formulário não conseguiu gerar o laudo.'))
      else if (dados.tipo === atual.tipo) atual.resolver(dados)
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  // Abre o formulário no iframe oculto e espera a mensagem `tipo`.
  function esperarFormulario(src: string, tipo: string, limiteMs: number) {
    return new Promise<MensagemDoFormulario>((resolve, reject) => {
      const terminar = () => {
        clearTimeout(timer)
        espera.current = null
        setIframeSrc(null)
      }
      const timer = setTimeout(() => {
        terminar()
        reject(new Error('O formulário demorou demais para responder. Tente de novo.'))
      }, limiteMs)
      espera.current = {
        tipo,
        resolver: (m) => {
          terminar()
          resolve(m)
        },
        rejeitar: (e) => {
          terminar()
          reject(e)
        },
      }
      setIframeSrc(src)
    })
  }

  // Catálogo do formulário, para laudos antigos que não guardaram uma cópia.
  const esperarRef = useRef(esperarFormulario)
  useEffect(() => {
    esperarRef.current = esperarFormulario
  })
  const obterCatalogo = useCallback(async () => {
    const { catalogo } = await esperarRef.current(`/formulario-novo-paciente.html?paciente=${pacienteId}&modo=catalogo`, 'laudo-ia:catalogo', 30000)
    if (!catalogo) throw new Error('Não foi possível ler os campos do protocolo.')
    return catalogo
  }, [pacienteId])

  // Resumo (sem fotos nem HTML) e pendências em paralelo. Se as pendências
  // falharem, o quadro "Campos que faltam" tenta de novo e mostra o erro.
  const abrirResumo = useCallback(
    (laudoId: string) =>
      Promise.all([
        getReportResumo(laudoId).then((r) => ({ ...r, answers_json: {}, generated_text: null }) as unknown as Laudo),
        carregarPendencias(laudoId, obterCatalogo).catch(() => null),
      ]),
    [obterCatalogo],
  )

  useEffect(() => {
    if (!laudoDoHistorico || laudo?.id === laudoDoHistorico) return
    let ativo = true
    abrirResumo(laudoDoHistorico)
      .then(([r, pendencias]) => {
        if (!ativo) return
        setPendenciasIniciais(pendencias)
        setLaudo(r)
        setErroAbertura(null)
        setEtapa('pronto')
      })
      .catch(() => { if (ativo) setErroAbertura('Não foi possível abrir o relatório. Volte ao histórico e tente novamente.') })
    return () => { ativo = false }
  }, [laudoDoHistorico, laudo?.id, abrirResumo])

  // "Atualizar relatório": aplica os dados confirmados, a IA encaixa os novos
  // no estudo de caso já escrito (sem reler os PDFs) e o formulário gera o
  // documento de novo (sem IA). A prévia só é baixada se ela pedir.
  async function atualizar(laudoId: string, reescreverEstudo: boolean) {
    setResultadoDaAtualizacao(null)
    try {
      setAtualizando('Aplicando os dados no relatório…')
      const r = await atualizarLaudo(laudoId, reescreverEstudo)
      if (r.job_id) await acompanharGeracao(r.job_id, (a) => setAtualizando(a.mensagem || 'Incluindo os dados novos no estudo de caso…'))
      setAtualizando('Gerando o documento com os dados novos…')
      await esperarFormulario(`/formulario-novo-paciente.html?laudo=${laudoId}&modo=gerar`, 'laudo-ia:gerado', 120000)
      setLaudo((atual) => (atual ? { ...atual, generated_text: null } : atual))
      setRecarregarPendencias((n) => n + 1)
      const estudo =
        r.estudo === 'reescrevendo' ? ' Os dados novos foram incluídos no estudo de caso.' : r.estudo === 'mantido_editado' ? ' O estudo de caso editado por você foi mantido.' : ''
      const campos = r.campos_aplicados === 1 ? '1 dado novo' : `${r.campos_aplicados} dados novos`
      setResultadoDaAtualizacao({ tom: 'success', texto: `Relatório atualizado com ${campos}.${estudo}` })
    } catch (e) {
      setResultadoDaAtualizacao({ tom: 'danger', texto: e instanceof Error ? e.message : 'Não foi possível atualizar o relatório.' })
    } finally {
      setAtualizando(null)
    }
  }

  async function gerar() {
    if (!dataRelatorio) { setErro('Informe a data do relatório.'); return }
    setErro(null)
    setLaudo(null)
    setLaudoSemDocumento(null)
    setAndamento(null)
    let criado: string | null = null
    try {
      setEtapa('catalogo')
      const { catalogo } = await esperarFormulario(`/formulario-novo-paciente.html?paciente=${pacienteId}&modo=catalogo`, 'laudo-ia:catalogo', 30000)
      if (!catalogo) throw new Error('Não foi possível ler os campos do protocolo.')
      setEtapa('ia')
      const novo = await gerarLaudoPorIA(pacienteId, arquivos, observacoes, catalogo, setAndamento, dataRelatorio, cidade)
      criado = novo.id
      setEtapa('documento')
      await esperarFormulario(`/formulario-novo-paciente.html?laudo=${novo.id}&modo=gerar`, 'laudo-ia:gerado', 120000)
      const [resumo, pendencias] = await abrirResumo(novo.id)
      setPendenciasIniciais(pendencias)
      setLaudo(resumo)
      setEtapa('pronto')
      // No endereço: recarregar ou voltar à página reabre este laudo e as pendências.
      setParams({ paciente: pacienteId, laudo: novo.id }, { replace: true })
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Não foi possível gerar o laudo.')
      setLaudoSemDocumento(criado)
      setEtapa('preencher')
    }
  }

  async function abrirPrevia() {
    if (!laudo || carregandoPrevia) return
    setCarregandoPrevia(true)
    try { setLaudo((await getReport(laudo.id)) as unknown as Laudo) }
    catch { setErro('Não foi possível carregar a prévia do relatório.') }
    finally { setCarregandoPrevia(false) }
  }

  // Formulário num iframe oculto (catálogo e geração do documento). Também na
  // tela de carregamento: relatórios antigos leem o catálogo antes de abrir.
  const formularioOculto = iframeSrc && (
    <iframe
      key={iframeSrc}
      src={iframeSrc}
      title="Gerando o laudo"
      aria-hidden="true"
      tabIndex={-1}
      style={{ position: 'fixed', left: -10000, top: 0, width: 1100, height: 800, border: 0 }}
    />
  )

  if (laudoDoHistorico && laudo?.id !== laudoDoHistorico) {
    return <div className="page-stack">
      <PageHeader eyebrow="Pacientes" title="Campos que faltam" description="Revise os dados e os métodos deste relatório." />
      {erroAbertura ? <Alert tone="danger">{erroAbertura}</Alert> : <p role="status" aria-live="polite">Carregando os campos que faltam…</p>}
      <Link to={`/pacientes/${pacienteId}/historico`} className={buttonClass('secondary')}>Voltar ao histórico</Link>
      {formularioOculto}
    </div>
  }

  const ocupado = etapa !== 'preencher' && etapa !== 'pronto'
  const nomeArquivo = (formato: 'pdf' | 'docx') => `laudo_ia_${(laudo?.answers_json?.nomePaciente as string | undefined)?.trim().replace(/\s+/g, '_') || 'paciente'}.${formato}`

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Pacientes"
        title="Relatório por IA"
        description="Envie os PDFs do Google Forms e das escalas (CARS, ATA, SNAP-IV…). A IA faz o estudo de caso, preenche o protocolo padrão e o sistema gera o laudo com os gráficos. Você revisa e edita o Word."
      />
      <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
        <EscolhaDePaciente
          id="paciente-laudo-ia"
          pacienteId={pacienteId}
          onEscolher={(id) => {
            setLaudo(null)
            setEtapa('preencher')
            setParams(id ? { paciente: id } : {}, { replace: true }) // sem ?laudo=
          }}
          onCadastrandoChange={setCadastrando}
        />

        {pacienteId && !cadastrando && etapa !== 'pronto' && (
          <Card title="PDFs do paciente" subtitle={`De 1 a ${MAXIMO_DE_PDFS_LAUDO} PDFs: respostas do Google Forms (responsáveis, escola) e escalas pontuadas. Cada escala enviada gera o seu gráfico no laudo.`}>
            <div style={{ display: 'grid', gap: 'var(--s-4)' }}>
              <div className="form-grid">
                <Input id="data-relatorio-ia" label="Data do relatório" type="date" required value={dataRelatorio} disabled={ocupado} onChange={(e) => setDataRelatorio(e.target.value)} />
                <Select id="cidade-relatorio-ia" label="Cidade do relatório (opcional)" placeholder="Selecione a cidade" value={cidade} disabled={ocupado} onChange={(e) => setCidade(e.target.value)} options={[
                  { value: 'Cidade Ocidental – GO', label: 'Cidade Ocidental – GO' },
                  { value: 'Gama – DF', label: 'Gama – DF' },
                ]} />
              </div>
              <SeletorDePdfs
                arquivos={arquivos}
                onChange={setArquivos}
                maximo={MAXIMO_DE_PDFS_LAUDO}
                problema={problemaNosPdfsDoLaudo}
                onErro={setErro}
                desabilitado={ocupado}
              />
              <Textarea
                id="observacoes-laudo-ia"
                label="Observações para a IA (opcional)"
                rows={2}
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Ex.: o PDF 'escola.pdf' foi respondido pela professora regente."
                disabled={ocupado}
              />
              <Alert tone="info">
                Os PDFs são enviados ao provedor de IA configurado em Configurações → Inteligência Artificial. A IA só preenche o que os PDFs sustentam — revise sempre o laudo antes de entregar.
              </Alert>
              {erro && (
                <Alert tone="danger">
                  {erro}
                  {laudoSemDocumento && (
                    <>
                      {' '}O laudo foi criado com as respostas da IA: <Link to={`/atendimento/novo?laudo=${laudoSemDocumento}`}>abra no formulário</Link> e clique em "Salvar laudo" para gerar o documento.
                    </>
                  )}
                </Alert>
              )}
              {ocupado && (
                <Alert tone="info">
                  {(etapa === 'ia' && andamento?.mensagem) || MENSAGEM_DA_ETAPA[etapa]}
                  {etapa === 'ia' && andamento && andamento.documentos.length > 1 && (
                    <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
                      {andamento.documentos.map((d) => (
                        <li key={d.nome}>
                          {d.nome}: {SITUACAO_DO_DOCUMENTO[d.status]}
                        </li>
                      ))}
                    </ul>
                  )}
                </Alert>
              )}
              <div>
                <Button icon={<Sparkles />} onClick={gerar} disabled={!arquivos.length || !dataRelatorio} loading={ocupado} loadingLabel="Gerando…">
                  Gerar relatório com IA
                </Button>
              </div>
            </div>
          </Card>
        )}

        {etapa === 'pronto' && laudo && (
          <Card title="Laudo gerado" subtitle="Mesmo modelo do protocolo padrão, com os gráficos. Baixe o Word para editar ou ajuste no formulário.">
            <div style={{ display: 'grid', gap: 'var(--s-4)' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
                <Button variant="tonal" icon={<Download />} onClick={() => downloadReportDocx(laudo.id, nomeArquivo('docx')).catch(() => setErro('Não foi possível gerar o Word.'))}>
                  Baixar Word (DOCX)
                </Button>
                <Button variant="tonal" icon={<FileText />} onClick={() => downloadReportPdf(laudo.id, nomeArquivo('pdf')).catch(() => setErro('Não foi possível gerar o PDF.'))}>
                  Baixar PDF
                </Button>
                <Button variant="secondary" icon={<PencilLine />} onClick={() => navigate(`/atendimento/novo?laudo=${laudo.id}`)}>
                  Ajustar no formulário
                </Button>
                <Link to={`/pacientes/${pacienteId}/historico`} className={buttonClass('ghost')}>
                  Ver histórico do paciente
                </Link>
              </div>
              {erro && <Alert tone="danger">{erro}</Alert>}
              <CamposQueFaltam
                key={laudo.id}
                laudoId={laudo.id}
                pendenciasIniciais={pendenciasIniciais ?? undefined}
                abrirAoCarregar
                pacienteId={pacienteId}
                obterCatalogo={obterCatalogo}
                recarregar={recarregarPendencias}
                gerando={!!atualizando}
                onGerar={(reescrever) => void atualizar(laudo.id, reescrever)}
              />
              {atualizando && <Alert tone="info">{atualizando}</Alert>}
              {resultadoDaAtualizacao && <Alert tone={resultadoDaAtualizacao.tom}>{resultadoDaAtualizacao.texto}</Alert>}
              <div className="report-next-action">
                <Button
                  type="button"
                  variant="primary"
                  icon={<Plus />}
                  size="lg"
                  disabled={!!atualizando}
                  onClick={() => {
                    setLaudo(null)
                    setPendenciasIniciais(null)
                    setArquivos([])
                    setEtapa('preencher')
                    setParams({ paciente: pacienteId }, { replace: true })
                  }}
                >
                  Gerar novo relatório
                </Button>
                <p>Inicie outro relatório para este paciente. O atual permanece salvo no histórico.</p>
              </div>
              {!laudo.generated_text && <Button variant="secondary" icon={<FileText />} loading={carregandoPrevia} loadingLabel="Carregando prévia…" onClick={() => void abrirPrevia()}>Ver prévia do relatório</Button>}
              {laudo.generated_text && (
                <iframe
                  title="Pré-visualização do laudo"
                  srcDoc={laudo.generated_text}
                  sandbox=""
                  className="doc-preview"
                  style={{ minHeight: '80vh' }}
                />
              )}

            </div>
          </Card>
        )}
      </div>

      {formularioOculto}
    </div>
  )
}
