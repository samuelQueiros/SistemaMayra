import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, PointerEvent as ReactPointerEvent } from 'react'
import { ApiError } from '../api/client'
import { fetchCapaUrl, me as getMe, removeCapa, updateCapaConfig, uploadCapa } from '../api/auth'
import type { CapaConfig } from '../api/types'
import { Upload } from 'lucide-react'
import { Alert, Button, Card, Checkbox } from './ds'

// Arte e faixa do nome usadas quando a psicóloga não envia capa própria —
// os mesmos valores de CAPA_ARTE_URL/CAPA_FAIXA em formulario-novo-paciente.html.
const ARTE_PADRAO = '/capa-relatorio.jpg'
const CONFIG_PADRAO: CapaConfig = {
  escreverNome: true,
  faixa: { x: 0.285, y: 0.4287, largura: 0.466, altura: 0.039 },
  corNome: '#ffffff',
}
const PROPORCAO_A4 = 210 / 297
const AREA_MINIMA = 0.01

type Faixa = CapaConfig['faixa']
type Ponto = { x: number; y: number }

const limitar = (v: number) => Math.min(1, Math.max(0, v))

function faixaEntre(a: Ponto, b: Ponto): Faixa {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    largura: Math.abs(a.x - b.x),
    altura: Math.abs(a.y - b.y),
  }
}

export function EditorCapa() {
  const [carregando, setCarregando] = useState(true)
  const [temCapa, setTemCapa] = useState(false)
  const [arteUrl, setArteUrl] = useState(ARTE_PADRAO)
  const [config, setConfig] = useState<CapaConfig>(CONFIG_PADRAO)
  const [foraDoA4, setForaDoA4] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState<string | null>(null)

  const previewRef = useRef<HTMLDivElement>(null)
  const inicioRef = useRef<Ponto | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let ativo = true
    getMe()
      .then(async (dados) => {
        if (!ativo) return
        setTemCapa(!!dados.tem_capa_personalizada)
        if (dados.capa_config) setConfig(dados.capa_config)
        else if (dados.tem_capa_personalizada) setConfig({ ...CONFIG_PADRAO, escreverNome: false })
        if (dados.tem_capa_personalizada) {
          const url = await fetchCapaUrl()
          if (ativo) setArteUrl(url)
        }
      })
      .catch(() => setErro('Não foi possível carregar a capa atual.'))
      .finally(() => ativo && setCarregando(false))
    return () => {
      ativo = false
    }
  }, [])

  useEffect(() => () => {
    if (arteUrl.startsWith('blob:')) URL.revokeObjectURL(arteUrl)
  }, [arteUrl])

  function aoCarregarArte(event: React.SyntheticEvent<HTMLImageElement>) {
    const img = event.currentTarget
    if (!img.naturalWidth || !img.naturalHeight) return
    const proporcao = img.naturalWidth / img.naturalHeight
    setForaDoA4(Math.abs(proporcao - PROPORCAO_A4) / PROPORCAO_A4 > 0.03)
  }

  async function aoEscolherArquivo(event: ChangeEvent<HTMLInputElement>) {
    const arquivo = event.target.files?.[0]
    event.target.value = ''
    if (!arquivo) return
    setEnviando(true)
    setErro(null)
    setSucesso(null)
    try {
      const dados = await uploadCapa(arquivo)
      setTemCapa(!!dados.tem_capa_personalizada)
      setArteUrl(URL.createObjectURL(arquivo))
      // Arte nova: a posição do nome da arte anterior provavelmente não
      // serve. Ela marca a área de novo, se quiser o nome.
      if (!dados.capa_config) setConfig({ ...CONFIG_PADRAO, escreverNome: false })
      setSucesso('Capa enviada. Se quiser o nome do paciente nela, marque a opção abaixo e desenhe a área do nome.')
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível enviar a capa.')
    } finally {
      setEnviando(false)
    }
  }

  async function voltarAoPadrao() {
    setErro(null)
    setSucesso(null)
    try {
      await removeCapa()
      setTemCapa(false)
      setArteUrl(ARTE_PADRAO)
      setConfig(CONFIG_PADRAO)
      setSucesso('A capa padrão do sistema voltou a ser usada.')
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível remover a capa.')
    }
  }

  async function salvar() {
    setSalvando(true)
    setErro(null)
    setSucesso(null)
    try {
      await updateCapaConfig(config)
      setSucesso('Capa salva. Os próximos relatórios já saem com ela.')
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível salvar a capa.')
    } finally {
      setSalvando(false)
    }
  }

  function pontoDoEvento(event: ReactPointerEvent<HTMLDivElement>): Ponto {
    const caixa = previewRef.current!.getBoundingClientRect()
    return {
      x: limitar((event.clientX - caixa.left) / caixa.width),
      y: limitar((event.clientY - caixa.top) / caixa.height),
    }
  }

  function aoPressionar(event: ReactPointerEvent<HTMLDivElement>) {
    if (!config.escreverNome) return
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    inicioRef.current = pontoDoEvento(event)
  }

  function aoMover(event: ReactPointerEvent<HTMLDivElement>) {
    if (!inicioRef.current) return
    const faixa = faixaEntre(inicioRef.current, pontoDoEvento(event))
    if (faixa.largura * faixa.altura < AREA_MINIMA / 100) return
    setConfig((c) => ({ ...c, faixa }))
  }

  function aoSoltar() {
    inicioRef.current = null
  }

  if (carregando) return null

  const { faixa } = config

  return (
    <Card
      title="Capa do relatório"
      subtitle="Primeira página de todo relatório (pré-visualização, PDF e Word). Cada relatório ainda pode trocar a capa dentro do formulário."
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-5)', alignItems: 'flex-start' }}>
        <div
          ref={previewRef}
          data-testid="preview-capa"
          onPointerDown={aoPressionar}
          onPointerMove={aoMover}
          onPointerUp={aoSoltar}
          onPointerCancel={aoSoltar}
          style={{
            position: 'relative',
            width: 'min(100%, 260px)',
            aspectRatio: '210 / 297',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-xs)',
            overflow: 'hidden',
            background: 'var(--n-0)',
            cursor: config.escreverNome ? 'crosshair' : 'default',
            touchAction: config.escreverNome ? 'none' : 'auto',
            userSelect: 'none',
          }}
        >
          <img
            src={arteUrl}
            alt="Prévia da capa do relatório"
            onLoad={aoCarregarArte}
            draggable={false}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', pointerEvents: 'none' }}
          />
          {config.escreverNome && (
            <div
              data-testid="area-nome"
              style={{
                position: 'absolute',
                left: `${faixa.x * 100}%`,
                top: `${faixa.y * 100}%`,
                width: `${faixa.largura * 100}%`,
                height: `${faixa.altura * 100}%`,
                outline: '2px dashed var(--sol-500)',
                containerType: 'size',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <span style={{ color: config.corNome, fontWeight: 600, fontSize: '60cqh', whiteSpace: 'nowrap', lineHeight: 1 }}>
                NOME DO PACIENTE
              </span>
            </div>
          )}
        </div>

        <div style={{ flex: '1 1 260px', display: 'grid', gap: 'var(--s-4)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
            <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.webp" hidden onChange={aoEscolherArquivo} data-testid="arquivo-capa" />
            <Button variant="secondary" icon={<Upload />} onClick={() => inputRef.current?.click()} loading={enviando} loadingLabel="Enviando…">
              {temCapa ? 'Trocar capa' : 'Enviar minha capa'}
            </Button>
            {temCapa && (
              <Button variant="ghost" onClick={voltarAoPadrao}>
                Voltar à capa padrão
              </Button>
            )}
          </div>
          <p className="caption" style={{ margin: 0 }}>
            Imagem JPG, PNG ou WEBP de até 10 MB, em pé, tamanho A4 (ideal 2480×3508). Feita no Canva? Exporte como
            PNG no tamanho A4.
          </p>
          {foraDoA4 && (
            <Alert tone="warning">
              Esta imagem não tem o formato de uma folha A4 em pé — ela será recortada ao centro para preencher a página.
            </Alert>
          )}

          <Checkbox
            label="Escrever o nome do paciente na capa"
            description={config.escreverNome ? 'Arraste sobre a prévia para marcar onde o nome fica.' : undefined}
            checked={config.escreverNome}
            onChange={(e) => setConfig((c) => ({ ...c, escreverNome: e.target.checked }))}
          />
          {config.escreverNome && (
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-3)', minHeight: 'var(--h-md)' }}>
              <input
                type="color"
                value={config.corNome}
                onChange={(e) => setConfig((c) => ({ ...c, corNome: e.target.value }))}
                aria-label="Cor do nome"
              />
              <span>Cor do nome</span>
            </label>
          )}

          {erro && <Alert tone="danger">{erro}</Alert>}
          {sucesso && <Alert tone="success">{sucesso}</Alert>}

          <Button onClick={salvar} loading={salvando} loadingLabel="Salvando…" style={{ justifySelf: 'start' }}>
            Salvar capa
          </Button>
        </div>
      </div>
    </Card>
  )
}
