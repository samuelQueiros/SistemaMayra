import { apiDelete, apiGet, apiPost, apiPut } from './client'
import type { ModeloProtocolo, Protocolo, RespostasProtocolo } from '../laudo/tipos'

export const listProtocolos = (incluirArquivados = false) =>
  apiGet<Protocolo[]>(`/protocolos${incluirArquivados ? '?incluir_arquivados=true' : ''}`)

export const getProtocolo = (id: string) => apiGet<Protocolo>(`/protocolos/${id}`)

export const createProtocolo = (modelo: ModeloProtocolo) =>
  apiPost<Protocolo>('/protocolos', { schema_json: modelo })

export const updateProtocolo = (id: string, modelo: ModeloProtocolo) =>
  apiPut<Protocolo>(`/protocolos/${id}`, { schema_json: modelo })

export const arquivarProtocolo = (id: string) => apiDelete<Protocolo>(`/protocolos/${id}`)

export const restaurarProtocolo = (id: string) => apiPost<Protocolo>(`/protocolos/${id}/restaurar`, {})

export const duplicarProtocolo = (id: string) => apiPost<Protocolo>(`/protocolos/${id}/duplicar`, {})

// Laudo de um atendimento feito com um modelo de protocolo. O backend guarda
// a cópia do modelo em computed_json.modelo (ver rules_engine/engine.py).
export interface LaudoProtocolo {
  id: string
  patient_id: string
  template_id: string
  answers_json: RespostasProtocolo
  computed_json: { modelo?: ModeloProtocolo } | null
  generated_text: string | null
  created_at: string
}

export const createLaudoProtocolo = (patientId: string, modeloId: string, respostas: RespostasProtocolo) =>
  apiPost<LaudoProtocolo>(`/patients/${patientId}/reports`, { template_id: modeloId, answers: respostas })

export const getLaudoProtocolo = (id: string) => apiGet<LaudoProtocolo>(`/reports/${id}`)

export const salvarRespostasLaudo = (id: string, respostas: RespostasProtocolo) =>
  apiPut<unknown>(`/reports/${id}/answers`, { answers: respostas })

export const salvarDocumentoLaudo = (id: string, html: string) =>
  apiPut<unknown>(`/reports/${id}/text`, { generated_text: html })
