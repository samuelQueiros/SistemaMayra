import { apiGet, apiPut, downloadGet, enviarFormulario } from './client'
import type { ExtrasRelatorioIA, RelatorioPorPdfs } from '../laudo/relatorioIA'

export interface LaudoRelatorioIA {
  id: string
  patient_id: string
  template_id: string
  answers_json: { arquivos: { nome: string; chave: string }[]; observacoes: string; extras?: ExtrasRelatorioIA }
  computed_json: { relatorio: RelatorioPorPdfs }
  generated_text: string | null
  created_at: string
}

export const MAXIMO_DE_PDFS = 6

const TAMANHO_MAXIMO = 15 * 1024 * 1024

// Valida a lista final de arquivos (mesmas regras do backend).
export function problemaNosArquivos(arquivos: File[]): string | null {
  if (arquivos.length > MAXIMO_DE_PDFS) return `Anexe no máximo ${MAXIMO_DE_PDFS} PDFs por relatório.`
  const naoPdf = arquivos.find((a) => !a.name.toLowerCase().endsWith('.pdf'))
  if (naoPdf) return `"${naoPdf.name}" não é um PDF. Exporte as respostas do Google Forms em PDF.`
  const grande = arquivos.find((a) => a.size > TAMANHO_MAXIMO)
  if (grande) return `"${grande.name}" passa de 15 MB.`
  return null
}

export function gerarRelatorioPorPdfs(patientId: string, arquivos: File[], observacoes: string) {
  const dados = new FormData()
  arquivos.forEach((a) => dados.append('arquivos', a))
  if (observacoes.trim()) dados.append('observacoes', observacoes.trim())
  return enviarFormulario<LaudoRelatorioIA>(`/patients/${patientId}/relatorios-pdf`, dados)
}

export const salvarRelatorioIA = (laudoId: string, relatorio: RelatorioPorPdfs, extras: ExtrasRelatorioIA) =>
  apiPut<LaudoRelatorioIA>(`/reports/${laudoId}/relatorio-ia`, { relatorio, extras })

export const baixarPdfOriginal = (laudoId: string, indice: number, nome: string) =>
  downloadGet(`/reports/${laudoId}/arquivos/${indice}`, nome)

export const getLaudoRelatorioIA = (laudoId: string) => apiGet<LaudoRelatorioIA>(`/reports/${laudoId}`)

export const salvarHtmlRelatorioIA = (laudoId: string, html: string) =>
  apiPut<unknown>(`/reports/${laudoId}/text`, { generated_text: html })
