import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Camera, FileImage, LoaderCircle, Paperclip, Trash2 } from 'lucide-react'
import { ApiError } from '../../api/client'
import { TIPOS_DE_ANEXO, apagarAnexo, enviarAnexo, listarAnexos, urlDoAnexo } from '../../api/anexos'
import type { Anexo } from '../../api/anexos'
import type { CatalogoDoProtocolo } from '../../api/laudoIA'
import type { GrupoPendente } from '../../api/pendencias'
import { Alert, Button, IconButton, Menu } from '../ds'
import { PendenciasDoLaudo } from './PendenciasDoLaudo'

// Consulta enquanto alguma foto está sendo lida pela IA.
const INTERVALO_DA_LEITURA_MS = 3000

interface Props {
  laudoId: string
  pacienteId: string
  obterCatalogo: () => Promise<CatalogoDoProtocolo>
  children?: (estado: { alterado: boolean; salvando: boolean }) => ReactNode
}

// Pendências do laudo + anexar foto ou documento (geral e por seção). A IA
// lê o anexo e as sugestões aparecem destacadas nos campos, para confirmar.
export function CompletarLaudo({ laudoId, pacienteId, obterCatalogo, children }: Props) {
  const [anexos, setAnexos] = useState<Anexo[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState<string | null>(null)
  const [recarregar, setRecarregar] = useState(0)
  const entradaCamera = useRef<HTMLInputElement>(null)
  const entradaArquivo = useRef<HTMLInputElement>(null)
  const secaoDoEnvio = useRef<string | undefined>(undefined)
  const prontos = useRef<Set<string>>(new Set())

  const atualizarAnexos = useCallback(async () => {
    const lista = await listarAnexos(pacienteId, laudoId)
    setAnexos(lista)
    // Leitura nova concluída: recarrega as pendências para mostrar as sugestões.
    const novos = lista.filter((a) => a.status === 'pronto' && !prontos.current.has(a.id))
    novos.forEach((a) => prontos.current.add(a.id))
    if (novos.some((a) => a.sugestoes > 0)) setRecarregar((n) => n + 1)
    return lista
  }, [pacienteId, laudoId])

  useEffect(() => {
    atualizarAnexos().catch(() => setErro('Não foi possível carregar os anexos.'))
  }, [atualizarAnexos])

  const lendo = anexos.some((a) => a.status === 'analisando')
  useEffect(() => {
    if (!lendo) return
    const timer = setInterval(() => void atualizarAnexos().catch(() => {}), INTERVALO_DA_LEITURA_MS)
    return () => clearInterval(timer)
  }, [lendo, atualizarAnexos])

  function escolher(entrada: HTMLInputElement | null, secao?: string) {
    secaoDoEnvio.current = secao
    entrada?.click()
  }

  async function enviar(arquivos: FileList | null) {
    const lista = Array.from(arquivos ?? [])
    setErro(null)
    for (const arquivo of lista) {
      setEnviando(arquivo.name)
      try {
        const anexo = await enviarAnexo(pacienteId, laudoId, arquivo, secaoDoEnvio.current)
        setAnexos((atual) => [...atual, anexo])
      } catch (e) {
        setErro(e instanceof ApiError ? e.message : `Não foi possível enviar "${arquivo.name}".`)
      }
    }
    setEnviando(null)
  }

  async function apagar(anexo: Anexo) {
    try {
      await apagarAnexo(pacienteId, anexo.id)
      setAnexos((atual) => atual.filter((a) => a.id !== anexo.id))
      setRecarregar((n) => n + 1)
    } catch {
      setErro(`Não foi possível apagar "${anexo.nome}".`)
    }
  }

  async function abrir(anexo: Anexo) {
    try {
      window.open(await urlDoAnexo(pacienteId, anexo.id), '_blank', 'noopener')
    } catch {
      setErro(`Não foi possível abrir "${anexo.nome}".`)
    }
  }

  const botaoAnexar = (rotulo: string, secao?: string, texto = 'Anexar') => (
    <Menu
      label={rotulo}
      text={texto}
      variant="secondary"
      icon={<Paperclip />}
      size="sm"
      items={[
        { label: 'Tirar foto', icon: <Camera />, onSelect: () => escolher(entradaCamera.current, secao) },
        { label: 'Escolher arquivo (foto ou PDF)', icon: <FileImage />, onSelect: () => escolher(entradaArquivo.current, secao) },
      ]}
    />
  )

  const situacao = (a: Anexo) =>
    a.status === 'analisando'
      ? 'lendo…'
      : a.status === 'erro'
        ? a.erro
        : a.sugestoes === 0
          ? 'nenhum dado novo encontrado'
          : `${a.sugestoes} ${a.sugestoes === 1 ? 'sugestão' : 'sugestões'} — confira abaixo`

  const topo = (
    <div style={{ display: 'grid', gap: 'var(--s-2)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-3)' }}>
        {botaoAnexar('Anexar foto ou documento', undefined, 'Anexar foto ou documento')}
        <span style={{ color: 'var(--text-2)', font: 'var(--type-caption)' }}>
          Ficha preenchida à mão, caderneta, relatório escolar ou laudo anterior: a IA sugere o preenchimento e você confirma.
        </span>
      </div>
      {enviando && (
        <span role="status" style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-2)', color: 'var(--text-2)' }}>
          <LoaderCircle aria-hidden="true" style={{ animation: 'spin 0.8s linear infinite' }} /> Enviando “{enviando}”…
        </span>
      )}
      {anexos.length > 0 && (
        <ul aria-label="Anexos" style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'grid', gap: 'var(--s-1)' }}>
          {anexos.map((a) => (
            <li key={a.id} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--s-2)' }}>
              <Button type="button" size="sm" variant="ghost" onClick={() => abrir(a)}>
                {a.nome}
              </Button>
              <span style={{ color: a.status === 'erro' ? 'var(--err-tx)' : 'var(--text-2)' }}>{situacao(a)}</span>
              <IconButton label={`Apagar ${a.nome}`} icon={<Trash2 />} size="sm" onClick={() => apagar(a)} />
            </li>
          ))}
        </ul>
      )}
      {erro && <Alert tone="danger">{erro}</Alert>}
    </div>
  )

  return (
    <>
      <input
        ref={entradaCamera}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        data-testid="anexo-camera"
        onChange={(e) => {
          void enviar(e.target.files)
          e.target.value = ''
        }}
      />
      <input
        ref={entradaArquivo}
        type="file"
        accept={TIPOS_DE_ANEXO}
        multiple
        hidden
        data-testid="anexo-arquivo"
        onChange={(e) => {
          void enviar(e.target.files)
          e.target.value = ''
        }}
      />
      <PendenciasDoLaudo
        laudoId={laudoId}
        pacienteId={pacienteId}
        obterCatalogo={obterCatalogo}
        recarregar={recarregar}
        topo={topo}
        acoesDaSecao={(g: GrupoPendente) => botaoAnexar(`Anexar foto ou documento para ${g.titulo}`, g.chave)}
      >
        {children}
      </PendenciasDoLaudo>
    </>
  )
}
