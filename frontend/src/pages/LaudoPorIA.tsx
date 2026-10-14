import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Download, FileText, PencilLine, Sparkles } from 'lucide-react'
import { ApiError } from '../api/client'
import { MAXIMO_DE_PDFS_LAUDO, gerarLaudoPorIA, problemaNosPdfsDoLaudo } from '../api/laudoIA'
import type { CatalogoDoProtocolo, LaudoPorIA as Laudo } from '../api/laudoIA'
import { downloadReportDocx, downloadReportPdf, getReport } from '../api/reports'
import { Alert, Button, Card, PageHeader, Textarea } from '../components/ds'
import { EscolhaDePaciente } from '../components/pacientes/EscolhaDePaciente'
import { SeletorDePdfs } from '../components/SeletorDePdfs'

type Etapa = 'preencher' | 'catalogo' | 'ia' | 'documento' | 'pronto'

const MENSAGEM_DA_ETAPA: Record<Etapa, string> = {
  preencher: '',
  catalogo: 'Preparando o protocolo do paciente…',
  ia: 'Um agente de IA por PDF está transcrevendo os arquivos; em seguida, os especialistas (anamnese, escalas, desenvolvimento e estudo de caso) preenchem o protocolo ao mesmo tempo…',
  documento: 'Gerando o laudo padrão com os gráficos…',
  pronto: '',
}

interface MensagemDoFormulario {
  tipo: string
  catalogo?: CatalogoDoProtocolo
  mensagem?: string
}

// Menu Pacientes → "Laudo Por IA": a psicóloga envia os PDFs (Google Forms e
// escalas), a IA escreve o estudo de caso e preenche o protocolo padrão, e o
// próprio formulário (num iframe oculto) gera o laudo oficial com os
// gráficos. Fluxo separado do preenchimento manual.
export default function LaudoPorIA() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const pacienteId = params.get('paciente') ?? ''
  const [cadastrando, setCadastrando] = useState(false)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [observacoes, setObservacoes] = useState('')
  const [etapa, setEtapa] = useState<Etapa>('preencher')
  const [erro, setErro] = useState<string | null>(null)
  const [laudo, setLaudo] = useState<Laudo | null>(null)
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

  async function gerar() {
    setErro(null)
    setLaudo(null)
    setLaudoSemDocumento(null)
    let criado: string | null = null
    try {
      setEtapa('catalogo')
      const { catalogo } = await esperarFormulario(`/formulario-novo-paciente.html?paciente=${pacienteId}&modo=catalogo`, 'laudo-ia:catalogo', 30000)
      if (!catalogo) throw new Error('Não foi possível ler os campos do protocolo.')
      setEtapa('ia')
      const novo = await gerarLaudoPorIA(pacienteId, arquivos, observacoes, catalogo)
      criado = novo.id
      setEtapa('documento')
      await esperarFormulario(`/formulario-novo-paciente.html?laudo=${novo.id}&modo=gerar`, 'laudo-ia:gerado', 120000)
      setLaudo((await getReport(novo.id)) as unknown as Laudo)
      setEtapa('pronto')
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Não foi possível gerar o laudo.')
      setLaudoSemDocumento(criado)
      setEtapa('preencher')
    }
  }

  const ocupado = etapa !== 'preencher' && etapa !== 'pronto'
  const nomeArquivo = (formato: 'pdf' | 'docx') => `laudo_ia_${(laudo?.answers_json?.nomePaciente as string | undefined)?.trim().replace(/\s+/g, '_') || 'paciente'}.${formato}`

  return (
    <div>
      <PageHeader
        eyebrow="Pacientes"
        title="Laudo Por IA"
        description="Envie os PDFs do Google Forms e das escalas (CARS, ATA, SNAP-IV…). A IA faz o estudo de caso, preenche o protocolo padrão e o sistema gera o laudo com os gráficos. Você revisa e edita o Word."
      />
      <div style={{ display: 'grid', gap: 'var(--np-space-5)' }}>
        <EscolhaDePaciente
          id="paciente-laudo-ia"
          pacienteId={pacienteId}
          onEscolher={(id) => {
            setLaudo(null)
            setEtapa('preencher')
            setParams(id ? { paciente: id } : {}, { replace: true })
          }}
          onCadastrandoChange={setCadastrando}
        />

        {pacienteId && !cadastrando && etapa !== 'pronto' && (
          <Card title="PDFs Do Paciente" subtitle={`De 1 a ${MAXIMO_DE_PDFS_LAUDO} PDFs: respostas do Google Forms (responsáveis, escola) e escalas pontuadas. Cada escala enviada gera o seu gráfico no laudo.`}>
            <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
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
                label="Observações Para A IA (Opcional)"
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
                      {' '}O laudo foi criado com as respostas da IA: <Link to={`/atendimento/novo?laudo=${laudoSemDocumento}`}>abra no formulário</Link> e clique em "Salvar Laudo" para gerar o documento.
                    </>
                  )}
                </Alert>
              )}
              {ocupado && <Alert tone="info">{MENSAGEM_DA_ETAPA[etapa]}</Alert>}
              <div>
                <Button type="button" icon={<Sparkles size={16} />} onClick={gerar} disabled={!arquivos.length || ocupado}>
                  {ocupado ? 'Gerando…' : 'Gerar Laudo Com IA'}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {etapa === 'pronto' && laudo && (
          <Card title="Laudo Gerado" subtitle="Mesmo modelo do protocolo padrão, com os gráficos. Baixe o Word para editar ou ajuste no formulário.">
            <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
              {laudo.computed_json.lacunas.length > 0 && (
                <Alert tone="warning">
                  <strong>Os PDFs não trouxeram:</strong>
                  <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
                    {laudo.computed_json.lacunas.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                </Alert>
              )}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
                <Button type="button" icon={<Download size={16} />} onClick={() => downloadReportDocx(laudo.id, nomeArquivo('docx')).catch(() => setErro('Não foi possível gerar o Word.'))}>
                  Baixar Word (DOCX)
                </Button>
                <Button type="button" variant="outline" icon={<FileText size={16} />} onClick={() => downloadReportPdf(laudo.id, nomeArquivo('pdf')).catch(() => setErro('Não foi possível gerar o PDF.'))}>
                  Baixar PDF
                </Button>
                <Button type="button" variant="outline" icon={<PencilLine size={16} />} onClick={() => navigate(`/atendimento/novo?laudo=${laudo.id}`)}>
                  Ajustar No Formulário
                </Button>
                <Link to={`/pacientes/${pacienteId}/historico`} style={{ alignSelf: 'center', color: 'var(--np-text-link)' }}>
                  Ver Histórico Do Paciente
                </Link>
              </div>
              {erro && <Alert tone="danger">{erro}</Alert>}
              {laudo.generated_text && (
                <iframe
                  title="Pré-Visualização Do Laudo"
                  srcDoc={laudo.generated_text}
                  sandbox=""
                  style={{ width: '100%', minHeight: '80vh', border: '1px solid var(--np-border)', borderRadius: 'var(--np-radius-md)', background: '#fff' }}
                />
              )}
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setLaudo(null)
                    setArquivos([])
                    setEtapa('preencher')
                  }}
                >
                  Gerar Outro Laudo
                </Button>
              </div>
            </div>
          </Card>
        )}
      </div>

      {iframeSrc && (
        <iframe
          key={iframeSrc}
          src={iframeSrc}
          title="Gerando O Laudo"
          aria-hidden="true"
          tabIndex={-1}
          style={{ position: 'fixed', left: -10000, top: 0, width: 1100, height: 800, border: 0 }}
        />
      )}
    </div>
  )
}
