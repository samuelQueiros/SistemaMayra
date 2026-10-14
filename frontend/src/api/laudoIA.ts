import { enviarFormulario } from './client'
import type { Report } from './types'

// Laudo Por IA: a IA lê os PDFs e preenche o protocolo padrão; o documento é
// gerado pelo próprio formulário (ver pages/LaudoPorIA.tsx).
export const MAXIMO_DE_PDFS_LAUDO = 10
const TAMANHO_MAXIMO = 15 * 1024 * 1024

export interface CatalogoDoProtocolo {
  campos: unknown[]
  contexto: string
}

export type LaudoPorIA = Omit<Report, 'computed_json'> & {
  computed_json: {
    origem: 'ia_pdf'
    arquivos: { nome: string; chave: string }[]
    lacunas: string[]
    campos_descartados: string[]
  }
}

export function problemaNosPdfsDoLaudo(arquivos: File[]): string | null {
  if (arquivos.length > MAXIMO_DE_PDFS_LAUDO) return `Anexe no máximo ${MAXIMO_DE_PDFS_LAUDO} PDFs.`
  const naoPdf = arquivos.find((a) => !a.name.toLowerCase().endsWith('.pdf'))
  if (naoPdf) return `"${naoPdf.name}" não é um PDF.`
  const grande = arquivos.find((a) => a.size > TAMANHO_MAXIMO)
  if (grande) return `"${grande.name}" passa de 15 MB.`
  return null
}

export function gerarLaudoPorIA(patientId: string, arquivos: File[], observacoes: string, catalogo: CatalogoDoProtocolo) {
  const dados = new FormData()
  arquivos.forEach((a) => dados.append('arquivos', a))
  dados.append('catalogo', JSON.stringify(catalogo))
  if (observacoes.trim()) dados.append('observacoes', observacoes.trim())
  return enviarFormulario<LaudoPorIA>(`/patients/${patientId}/laudo-ia`, dados)
}
