import { useCallback, useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowDown, ArrowLeft, ArrowUp, BarChart3, Download, Eye, FileText, Plus, Save, Trash2 } from 'lucide-react'
import { ApiError, downloadBlob } from '../api/client'
import { me as getMe } from '../api/auth'
import { getPatient } from '../api/patients'
import { baixarPdfOriginal, getLaudoRelatorioIA, salvarHtmlRelatorioIA, salvarRelatorioIA } from '../api/relatoriosPdf'
import type { LaudoRelatorioIA } from '../api/relatoriosPdf'
import type { Patient, Psychologist } from '../api/types'
import { Alert, Button, buttonClass, Card, Checkbox, IconButton, Input, PageHeader, SaveStatus, Textarea } from '../components/ds'
import { nomeParaExibicao } from '../utils/exibicao'
import { CAPA_CONFIG_SISTEMA, prepararCapaA4 } from '../laudo/imagens'
import { TITULO_PADRAO, gerarDocumentoRelatorioIA } from '../laudo/relatorioIA'
import type { AreaDoRelatorio, ExtrasRelatorioIA, GraficoDaArea, RelatorioPorPdfs as Relatorio } from '../laudo/relatorioIA'
import type { Identificacao } from '../laudo/tipos'

const ATRASO_AUTOSAVE_MS = 1200

const hojeISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function mover<T>(lista: T[], de: number, para: number): T[] {
  if (para < 0 || para >= lista.length) return lista
  const copia = [...lista]
  const [item] = copia.splice(de, 1)
  copia.splice(para, 0, item)
  return copia
}

const nomeArquivo = (nome: string) => 'Relatorio_' + (nome.trim() || 'Paciente').replace(/[^a-zA-Z0-9À-ÿ]+/g, '_')

// Tela de revisão do relatório gerado por IA a partir dos PDFs de
// formulários: tudo editável, salvamento automático, prévia, PDF e Word.
export default function RelatorioPorPdfs() {
  const { id: pacienteId, laudoId } = useParams()
  const navigate = useNavigate()
  const [laudo, setLaudo] = useState<LaudoRelatorioIA | null>(null)
  const [paciente, setPaciente] = useState<Patient | null>(null)
  const [perfil, setPerfil] = useState<Psychologist | null>(null)
  const [relatorio, setRelatorio] = useState<Relatorio | null>(null)
  const [extras, setExtras] = useState<ExtrasRelatorioIA>({ titulo: TITULO_PADRAO, cidade: '', data_relatorio: hojeISO(), responsavel: '', capa: null })
  const [erro, setErro] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [previa, setPrevia] = useState<string | null>(null)
  const temporizador = useRef<number | undefined>(undefined)
  const pendente = useRef(false)

  useEffect(() => {
    Promise.all([getLaudoRelatorioIA(laudoId!), getPatient(pacienteId!), getMe()])
      .then(([l, p, eu]) => {
        setLaudo(l)
        setPaciente(p)
        setPerfil(eu)
        setRelatorio(l.computed_json.relatorio)
        if (l.answers_json.extras) setExtras((atual) => ({ ...atual, ...l.answers_json.extras }))
      })
      .catch((e) => setErro(e instanceof ApiError ? e.message : 'Não foi possível abrir o relatório.'))
  }, [laudoId, pacienteId])

  useEffect(() => {
    function antesDeSair(e: BeforeUnloadEvent) {
      if (!pendente.current) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', antesDeSair)
    return () => window.removeEventListener('beforeunload', antesDeSair)
  }, [])

  const agendarSalvamento = useCallback(
    (r: Relatorio, x: ExtrasRelatorioIA) => {
      pendente.current = true
      setStatus('Salvando alterações…')
      window.clearTimeout(temporizador.current)
      temporizador.current = window.setTimeout(async () => {
        try {
          await salvarRelatorioIA(laudoId!, r, x)
          pendente.current = false
          setStatus(`✓ Alterações salvas às ${new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}.`)
        } catch (e) {
          setStatus('Alterações ainda não salvas: ' + (e instanceof ApiError ? e.message : 'erro de conexão.'))
        }
      }, ATRASO_AUTOSAVE_MS)
    },
    [laudoId],
  )

  const alterar = (mudanca: (r: Relatorio) => Relatorio) => {
    if (!relatorio) return
    const novo = mudanca(relatorio)
    setRelatorio(novo)
    agendarSalvamento(novo, extras)
  }
  const alterarExtras = (mudanca: Partial<ExtrasRelatorioIA>) => {
    const novo = { ...extras, ...mudanca }
    setExtras(novo)
    if (relatorio) agendarSalvamento(relatorio, novo)
  }
  const alterarArea = (i: number, mudanca: Partial<AreaDoRelatorio>) =>
    alterar((r) => ({ ...r, areas: r.areas.map((a, k) => (k === i ? { ...a, ...mudanca } : a)) }))

  if (erro && !relatorio) return <Alert tone="danger">{erro}</Alert>
  if (!laudo || !paciente || !perfil || !relatorio) return <p className="text-2">Carregando…</p>

  const identificacao: Identificacao = {
    nome: paciente.name,
    data_nascimento: paciente.birth_date,
    sexo: paciente.sex ?? '',
    responsavel: extras.responsavel,
    cidade: extras.cidade,
    data_relatorio: extras.data_relatorio,
  }
  const documento = () => gerarDocumentoRelatorioIA(relatorio, identificacao, extras, perfil)

  async function preVisualizar() {
    setOcupado('previa')
    setErro(null)
    try {
      setPrevia(await documento())
    } catch {
      setErro('Não foi possível montar a pré-visualização.')
    } finally {
      setOcupado(null)
    }
  }

  async function exportar(formato: 'pdf' | 'docx') {
    setOcupado(formato)
    setErro(null)
    try {
      const nome = nomeArquivo(paciente!.name)
      await downloadBlob(`/documents/${formato}`, { html: await documento(), file_name: nome }, `${nome}.${formato}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : `Não foi possível gerar o ${formato === 'pdf' ? 'PDF' : 'Word'}.`)
    } finally {
      setOcupado(null)
    }
  }

  async function salvarEVoltar() {
    setOcupado('salvar')
    setErro(null)
    try {
      window.clearTimeout(temporizador.current)
      await salvarRelatorioIA(laudoId!, relatorio!, extras)
      await salvarHtmlRelatorioIA(laudoId!, await documento())
      pendente.current = false
      navigate(`/pacientes/${pacienteId}/historico`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível salvar o relatório.')
      setOcupado(null)
    }
  }

  async function trocarCapa(e: ChangeEvent<HTMLInputElement>) {
    const arquivo = e.target.files?.[0]
    e.target.value = ''
    if (!arquivo) return
    const { src } = await prepararCapaA4(arquivo)
    const config = perfil!.capa_config ?? (perfil!.tem_capa_personalizada ? { ...CAPA_CONFIG_SISTEMA, escreverNome: false } : CAPA_CONFIG_SISTEMA)
    alterarExtras({ capa: { src, config } })
  }

  return (
    <div>
      <PageHeader
        eyebrow={`Histórico · ${nomeParaExibicao(paciente.name)}`}
        title="Relatório por IA (formulários)"
        description="Revise e ajuste o que a IA escreveu. As alterações são salvas automaticamente."
        meta={status.startsWith('Alterações ainda não salvas') ? <span className="caption">{status}</span> : undefined}
        actions={
          <>
            <SaveStatus status={status} salvo />
            <Link to={`/pacientes/${pacienteId}/historico`} className={buttonClass('ghost')}>
              <ArrowLeft aria-hidden="true" /> Voltar ao histórico
            </Link>
          </>
        }
      />

      <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
        {erro && <Alert tone="danger">{erro}</Alert>}

        <Card title="Formulários analisados" subtitle="PDFs enviados para a IA. Clique para baixar o original.">
          <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
            {laudo.answers_json.arquivos.map((arq, i) => {
              const lido = relatorio.formularios.find((f) => f.arquivo === arq.nome) ?? relatorio.formularios[i]
              return (
                <div key={arq.chave} style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)', alignItems: 'center' }}>
                  <Button variant="secondary" size="sm" icon={<Download />} onClick={() => baixarPdfOriginal(laudo.id, i, arq.nome)}>
                    {arq.nome}
                  </Button>
                  {lido && (
                    <span className="caption">
                      {[lido.titulo, lido.respondente, lido.data].filter(Boolean).join(' · ')}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </Card>

        <Card title="Identificação e título">
          <div className="form-grid">
            <Input label="Responsável" value={extras.responsavel} onChange={(e) => alterarExtras({ responsavel: e.target.value })} />
            <Input label="Cidade (assinatura)" value={extras.cidade} onChange={(e) => alterarExtras({ cidade: e.target.value })} placeholder="Ex.: Gama – DF" />
            <Input label="Data do relatório" type="date" value={extras.data_relatorio} onChange={(e) => alterarExtras({ data_relatorio: e.target.value })} />
          </div>
          <div style={{ marginTop: 'var(--s-4)' }}>
            <Textarea id="titulo-relatorio-ia" label="Título do relatório" rows={2} value={extras.titulo} onChange={(e) => alterarExtras({ titulo: e.target.value })} />
          </div>
        </Card>

        <Card title="Metodologia">
          <Textarea id="metodologia-ia" rows={4} value={relatorio.metodologia} onChange={(e) => alterar((r) => ({ ...r, metodologia: e.target.value }))} />
        </Card>

        {relatorio.areas.map((area, i) => (
          <Card
            key={i}
            title={area.titulo || `Área ${i + 1}`}
            subtitle={area.fontes.length ? `Fontes: ${area.fontes.join('; ')}` : undefined}
            action={
              <div style={{ display: 'flex', gap: 'var(--s-2)' }}>
                <IconButton label="Mover para cima" icon={<ArrowUp size={16} />} variant="ghost" size="sm" disabled={i === 0} onClick={() => alterar((r) => ({ ...r, areas: mover(r.areas, i, i - 1) }))} />
                <IconButton
                  label="Mover para baixo"
                  icon={<ArrowDown size={16} />}
                  variant="ghost"
                  size="sm"
                  disabled={i === relatorio.areas.length - 1}
                  onClick={() => alterar((r) => ({ ...r, areas: mover(r.areas, i, i + 1) }))}
                />
                <IconButton
                  label="Remover área"
                  icon={<Trash2 size={16} />}
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (confirm(`Remover a área "${area.titulo}" do relatório?`)) alterar((r) => ({ ...r, areas: r.areas.filter((_, k) => k !== i) }))
                  }}
                />
              </div>
            }
          >
            <div style={{ display: 'grid', gap: 'var(--s-4)' }}>
              <Input label="Título da área" value={area.titulo} onChange={(e) => alterarArea(i, { titulo: e.target.value })} />
              <Textarea id={`texto-area-${i}`} label="Texto" rows={7} value={area.texto} onChange={(e) => alterarArea(i, { texto: e.target.value })} />
              <EditorGrafico grafico={area.grafico ?? null} onChange={(grafico) => alterarArea(i, { grafico })} />
            </div>
          </Card>
        ))}

        <Button
          type="button"
          variant="secondary"
          icon={<Plus size={16} />}
          style={{ justifySelf: 'start' }}
          onClick={() => alterar((r) => ({ ...r, areas: [...r.areas, { titulo: 'Nova área', texto: '', fontes: [], grafico: null }] }))}
        >
          Adicionar área
        </Button>

        <Card title="Considerações finais e sugestões">
          <div style={{ display: 'grid', gap: 'var(--s-4)' }}>
            <Textarea id="consideracoes-ia" label="Considerações finais" rows={6} value={relatorio.consideracoes_finais} onChange={(e) => alterar((r) => ({ ...r, consideracoes_finais: e.target.value }))} />
            <Textarea
              id="sugestoes-ia"
              label="Sugestões de intervenção"
              rows={6}
              value={relatorio.sugestoes_intervencao}
              onChange={(e) => alterar((r) => ({ ...r, sugestoes_intervencao: e.target.value }))}
              hint="Linhas começando com • viram lista; **negrito** e ==destaque cinza== funcionam como no protocolo."
            />
          </div>
        </Card>

        <Card title="Capa deste relatório (opcional)" subtitle="Por padrão usa a capa de Configurações → Capa dos relatórios.">
          <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
            <input type="file" accept=".jpg,.jpeg,.png,.webp" onChange={trocarCapa} aria-label="Enviar capa deste relatório" />
            {extras.capa && (
              <div style={{ display: 'flex', gap: 'var(--s-4)', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <img src={extras.capa.src} alt="Capa deste relatório" style={{ width: 140, border: '1px solid var(--border)', borderRadius: 'var(--r-xs)' }} />
                <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
                  <Checkbox
                    label="Escrever o nome do paciente na capa"
                    checked={extras.capa.config.escreverNome}
                    onChange={(e) => alterarExtras({ capa: { ...extras.capa!, config: { ...extras.capa!.config, escreverNome: e.target.checked } } })}
                  />
                  <Button type="button" variant="secondary" size="sm" style={{ justifySelf: 'start' }} onClick={() => alterarExtras({ capa: null })}>
                    Usar a capa padrão
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card title="Relatório">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
            <Button variant="secondary" icon={<Eye />} onClick={preVisualizar} loading={ocupado === 'previa'} loadingLabel="Montando…" disabled={!!ocupado}>
              Pré-visualizar
            </Button>
            <Button variant="tonal" icon={<Download />} onClick={() => exportar('pdf')} loading={ocupado === 'pdf'} loadingLabel="Gerando PDF…" disabled={!!ocupado}>
              PDF
            </Button>
            <Button variant="tonal" icon={<FileText />} onClick={() => exportar('docx')} loading={ocupado === 'docx'} loadingLabel="Gerando Word…" disabled={!!ocupado}>
              Word
            </Button>
            <span style={{ flex: 1 }} />
            <Button icon={<Save />} onClick={salvarEVoltar} loading={ocupado === 'salvar'} loadingLabel="Salvando…" disabled={!!ocupado}>
              Salvar e voltar ao histórico
            </Button>
          </div>
          {previa && (
            <iframe
              title="Pré-visualização do relatório"
              sandbox="" srcDoc={previa}
              className="doc-preview"
              style={{ height: 1000, marginTop: 'var(--s-4)' }}
            />
          )}
        </Card>
      </div>
    </div>
  )
}

function EditorGrafico({ grafico, onChange }: { grafico: GraficoDaArea | null; onChange: (g: GraficoDaArea | null) => void }) {
  if (!grafico) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="sm"
        icon={<BarChart3 size={14} />}
        style={{ justifySelf: 'start' }}
        onClick={() => onChange({ titulo: '', rotulos: [''], valores: [0], maximo: null, regua: '' })}
      >
        Adicionar gráfico
      </Button>
    )
  }
  const mudarLinha = (k: number, rotulo: string, valor: number) =>
    onChange({
      ...grafico,
      rotulos: grafico.rotulos.map((r, n) => (n === k ? rotulo : r)),
      valores: grafico.valores.map((v, n) => (n === k ? valor : v)),
    })
  return (
    <fieldset style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: 'var(--s-3)', display: 'grid', gap: 'var(--s-3)' }}>
      <legend style={{ font: 'var(--type-label)', padding: '0 4px' }}>Gráfico (valores editáveis)</legend>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr)', gap: 'var(--s-3)' }}>
        <Input label="Título do gráfico" value={grafico.titulo} onChange={(e) => onChange({ ...grafico, titulo: e.target.value })} />
        <Input
          label="Valor máximo (opcional)"
          type="number"
          step="any"
          value={grafico.maximo ?? ''}
          onChange={(e) => onChange({ ...grafico, maximo: e.target.value === '' ? null : Number(e.target.value) })}
        />
      </div>
      {grafico.rotulos.map((rotulo, k) => (
        <div key={k} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,3fr) minmax(0,1fr) auto', gap: 'var(--s-2)', alignItems: 'end' }}>
          <Input label={k === 0 ? 'Barra' : undefined} value={rotulo} onChange={(e) => mudarLinha(k, e.target.value, grafico.valores[k])} />
          <Input label={k === 0 ? 'Valor' : undefined} type="number" step="any" value={grafico.valores[k]} onChange={(e) => mudarLinha(k, rotulo, Number(e.target.value))} />
          <IconButton
            label="Remover barra"
            icon={<Trash2 size={14} />}
            variant="ghost"
            size="sm"
            disabled={grafico.rotulos.length === 1}
            onClick={() => onChange({ ...grafico, rotulos: grafico.rotulos.filter((_, n) => n !== k), valores: grafico.valores.filter((_, n) => n !== k) })}
          />
        </div>
      ))}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' }}>
        <Button type="button" variant="ghost" size="sm" icon={<Plus size={14} />} onClick={() => onChange({ ...grafico, rotulos: [...grafico.rotulos, ''], valores: [...grafico.valores, 0] })}>
          Adicionar barra
        </Button>
        <Button type="button" variant="ghost" size="sm" icon={<Trash2 size={14} />} onClick={() => onChange(null)}>
          Remover gráfico
        </Button>
      </div>
      <Input label="Como os valores foram obtidos" value={grafico.regua} onChange={(e) => onChange({ ...grafico, regua: e.target.value })} />
    </fieldset>
  )
}
