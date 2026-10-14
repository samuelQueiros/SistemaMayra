import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { FileUp, Trash2 } from 'lucide-react'
import { Button, IconButton } from './ds'

const tamanho = (bytes: number) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`)

// Área de arrastar/escolher PDFs + lista dos escolhidos (Relatório Por IA e
// Laudo Por IA). `problema` valida a lista final; o erro vai para `onErro`.
export function SeletorDePdfs({
  arquivos,
  onChange,
  maximo,
  problema,
  onErro,
  desabilitado = false,
}: {
  arquivos: File[]
  onChange: (arquivos: File[]) => void
  maximo: number
  problema: (arquivos: File[]) => string | null
  onErro: (mensagem: string | null) => void
  desabilitado?: boolean
}) {
  const [arrastando, setArrastando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function adicionar(novos: File[]) {
    const lista = [...arquivos, ...novos.filter((n) => !arquivos.some((a) => a.name === n.name && a.size === n.size))]
    const erro = problema(lista)
    onErro(erro)
    if (!erro) onChange(lista)
  }

  function soltar(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setArrastando(false)
    if (!desabilitado) adicionar(Array.from(e.dataTransfer.files))
  }

  return (
    <>
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
        <Button type="button" variant="outline" icon={<FileUp size={16} />} onClick={() => inputRef.current?.click()} disabled={arquivos.length >= maximo || desabilitado}>
          Escolher PDFs ({arquivos.length}/{maximo})
        </Button>
      </div>

      {arquivos.length > 0 && (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--np-space-2)' }}>
          {arquivos.map((a, i) => (
            <li key={a.name + a.size} style={{ display: 'flex', alignItems: 'center', gap: 'var(--np-space-3)' }}>
              <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.name}</span>
              <span style={{ font: 'var(--np-type-caption)', color: 'var(--np-text-muted)' }}>{tamanho(a.size)}</span>
              <IconButton label={`Remover ${a.name}`} icon={<Trash2 size={16} />} variant="ghost" size="sm" disabled={desabilitado} onClick={() => onChange(arquivos.filter((_, k) => k !== i))} />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
