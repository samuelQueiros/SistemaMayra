import { ApiError, apiGet, enviarFormulario } from './client'
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

// Andamento da geração em segundo plano (GET /api/laudo-ia/jobs/{id}).
export interface AndamentoDoLaudoIA {
  id: string
  status: 'na_fila' | 'processando' | 'concluido' | 'erro'
  mensagem: string
  documentos: { nome: string; status: 'aguardando' | 'lendo' | 'lido' | 'erro' }[]
  report_id: string | null
  erro: string | null
}

const INTERVALO_DE_CONSULTA_MS = 2000
// Falhas passageiras seguidas (rede ou servidor) toleradas ao consultar o
// andamento: a geração continua no servidor mesmo se a conexão oscilar.
const FALHAS_PASSAGEIRAS_TOLERADAS = 5

const esperar = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Começa a geração e acompanha até o fim; devolve o id do laudo criado.
export async function gerarLaudoPorIA(
  patientId: string,
  arquivos: File[],
  observacoes: string,
  catalogo: CatalogoDoProtocolo,
  aoProgredir?: (andamento: AndamentoDoLaudoIA) => void,
): Promise<{ id: string }> {
  const dados = new FormData()
  arquivos.forEach((a) => dados.append('arquivos', a))
  dados.append('catalogo', JSON.stringify(catalogo))
  if (observacoes.trim()) dados.append('observacoes', observacoes.trim())
  const { job_id } = await enviarFormulario<{ job_id: string }>(`/patients/${patientId}/laudo-ia`, dados)
  return acompanharGeracao(job_id, aoProgredir)
}

// Acompanha uma geração em segundo plano até o fim; devolve o id do laudo.
export async function acompanharGeracao(job_id: string, aoProgredir?: (andamento: AndamentoDoLaudoIA) => void): Promise<{ id: string }> {
  let falhasSeguidas = 0
  for (;;) {
    await esperar(INTERVALO_DE_CONSULTA_MS)
    let andamento: AndamentoDoLaudoIA
    try {
      andamento = await apiGet<AndamentoDoLaudoIA>(`/laudo-ia/jobs/${job_id}`)
      falhasSeguidas = 0
    } catch (e) {
      const passageira = e instanceof ApiError && (e.status === 0 || e.status >= 500)
      if (passageira && ++falhasSeguidas <= FALHAS_PASSAGEIRAS_TOLERADAS) continue
      throw e
    }
    aoProgredir?.(andamento)
    if (andamento.status === 'concluido' && andamento.report_id) return { id: andamento.report_id }
    if (andamento.status === 'erro') throw new Error(andamento.erro || 'Não foi possível gerar o laudo.')
  }
}
