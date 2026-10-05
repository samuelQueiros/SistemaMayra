import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileUp, Sparkles, Trash2 } from 'lucide-react'
import { ApiError } from '../api/client'
import { MAXIMO_DE_PDFS, gerarRelatorioPorPdfs, problemaNosArquivos } from '../api/relatoriosPdf'
import { Alert, Button, Card, IconButton, Textarea } from './ds'

const tamanho = (bytes: number) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`)

// Histórico do paciente: anexar de 1 a 6 PDFs de respostas (Google Forms)
// para a IA gerar o relatório por área/tema, que abre na tela de revisão.
export function EnvioDePdfsParaIA({ patientId, abertoInicial = false }: { patientId: string; abertoInicial?: boolean }) {
  const navigate = useNavigate()
  const [aberto, setAberto] = useState(abertoInicial)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [observacoes, setObservacoes] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [gerando, setGerando] = useState(false)
  const [arrastando, setArrastando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function adicionar(novos: File[]) {
    const lista = [...arquivos, ...novos.filter((n) => !arquivos.some((a) => a.name === n.name && a.size === n.size))]
    const problema = problemaNosArquivos(lista)
    setErro(problema)
    if (!problema) setArquivos(lista)
  }

  function soltar(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setArrastando(false)
    adicionar(Array.from(e.dataTransfer.files))
  }

  async function gerar() {
    setErro(null)
    setGerando(true)
    try {
      const laudo = await gerarRelatorioPorPdfs(patientId, arquivos, observacoes)
      navigate(`/pacientes/${patientId}/relatorio-ia/${laudo.id}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível gerar o relatório.')
      setGerando(false)
    }
  }

  if (!aberto) {
    return (
      <Card style={{ marginTop: 'var(--np-space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-4)', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600 }}>Relatório Por IA A Partir De Formulários</div>
            <div style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>
              Anexe até {MAXIMO_DE_PDFS} PDFs com as respostas (ex.: Google Forms). A IA lê perguntas e respostas e monta o relatório por área, com gráficos, para você revisar.
            </div>
          </div>
          <Button type="button" icon={<Sparkles size={16} />} onClick={() => setAberto(true)}>
            Relatório Por IA (PDFs)
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card
      title="Relatório Por IA A Partir De Formulários"
      subtitle={`Anexe de 1 a ${MAXIMO_DE_PDFS} PDFs com as respostas. No Google Forms: aba Respostas → Individual → ícone de impressora → Salvar como PDF.`}
      style={{ marginTop: 'var(--np-space-5)' }}
    >
      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <div
          data-testid="area-pdfs"
          onDragOver={(e) => {
            e.preventDefault()
            setArrastando(true)
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={soltar}
          style={{
            border: `2px dashed ${arrastando ? 'var(--np-primary)' : 'var(--np-border-strong)'}`,
            borderRadius: 'var(--np-radius-md)',
            padding: 'var(--np-space-5)',
            textAlign: 'center',
            background: arrastando ? 'var(--np-surface-alt)' : 'transparent',
          }}
        >
          <p style={{ marginTop: 0 }}>Arraste os PDFs para cá ou</p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            hidden
            data-testid="arquivos-pdf"
            onChange={(e) => {
              adicionar(Array.from(e.target.files ?? []))
              e.target.value = ''
            }}
          />
          <Button type="button" variant="outline" icon={<FileUp size={16} />} onClick={() => inputRef.current?.click()} disabled={arquivos.length >= MAXIMO_DE_PDFS || gerando}>
            Escolher PDFs ({arquivos.length}/{MAXIMO_DE_PDFS})
          </Button>
        </div>

        {arquivos.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--np-space-2)' }}>
            {arquivos.map((a, i) => (
              <li key={a.name + a.size} style={{ display: 'flex', alignItems: 'center', gap: 'var(--np-space-3)' }}>
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.name}</span>
                <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{tamanho(a.size)}</span>
                <IconButton label={`Remover ${a.name}`} icon={<Trash2 size={16} />} variant="ghost" size="sm" disabled={gerando} onClick={() => setArquivos(arquivos.filter((_, k) => k !== i))} />
              </li>
            ))}
          </ul>
        )}

        <Textarea
          id="observacoes-ia"
          label="Observações Para A IA (Opcional)"
          rows={2}
          value={observacoes}
          onChange={(e) => setObservacoes(e.target.value)}
          placeholder="Ex.: dar atenção especial à comunicação e ao comportamento em sala."
        />
        <Alert tone="info">
          Os PDFs são enviados ao provedor de IA configurado em Configurações → Inteligência Artificial para leitura. Revise sempre o relatório antes de exportar.
        </Alert>
        {erro && <Alert tone="danger">{erro}</Alert>}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
          <Button type="button" icon={<Sparkles size={16} />} onClick={gerar} disabled={!arquivos.length || gerando}>
            {gerando ? 'Lendo os formulários… (pode levar 1 a 2 minutos)' : 'Gerar Relatório'}
          </Button>
          <Button type="button" variant="ghost" disabled={gerando} onClick={() => setAberto(false)}>
            Cancelar
          </Button>
        </div>
      </div>
    </Card>
  )
}
