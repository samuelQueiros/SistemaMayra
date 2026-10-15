import { apiDelete, apiGet, enviarFormulario, fetchObjectUrl } from './client'

// Fotos/documentos anexados para completar as pendências de um laudo; a IA
// lê em segundo plano e sugere valores (ver backend/app/api/anexos.py).
export interface Anexo {
  id: string
  nome: string
  mime: string
  secao: string | null
  status: 'analisando' | 'pronto' | 'erro'
  erro: string | null
  sugestoes: number
  created_at: string
}

export const TIPOS_DE_ANEXO = 'image/jpeg,image/png,image/webp,application/pdf'

export function enviarAnexo(pacienteId: string, laudoId: string, arquivo: File, secao?: string) {
  const dados = new FormData()
  dados.append('arquivo', arquivo)
  dados.append('report_id', laudoId)
  if (secao) dados.append('secao', secao)
  return enviarFormulario<Anexo>(`/patients/${pacienteId}/anexos`, dados)
}

export const listarAnexos = (pacienteId: string, laudoId: string) =>
  apiGet<Anexo[]>(`/patients/${pacienteId}/anexos?report_id=${encodeURIComponent(laudoId)}`)

export const urlDoAnexo = (pacienteId: string, anexoId: string) => fetchObjectUrl(`/patients/${pacienteId}/anexos/${anexoId}/arquivo`)

export const apagarAnexo = (pacienteId: string, anexoId: string) =>
  apiDelete<void>(`/patients/${pacienteId}/anexos/${anexoId}`)
