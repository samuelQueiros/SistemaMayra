import { apiGet, apiPatch, apiPost, apiPut } from './client'
import type { CatalogoDoProtocolo } from './laudoIA'

// Pendências de um laudo (o que faltou depois do Laudo por IA), calculadas
// pelo backend — ver backend/app/services/pendencias.py.

export type Situacao = 'preenchido' | 'nao_se_aplica' | 'nao_informado'
export type Valor = string | boolean | number | null

export interface CampoDaPendencia {
  id: string
  tipo: 'opcao' | 'simnao' | 'numero' | 'texto' | 'data'
  opcoes: { valor: string; rotulo: string }[]
  min: number | null
  max: number | null
}

export interface SugestaoDeAnexo {
  campo_id: string
  valor: string
  trecho?: string
  anexo_id: string
  anexo_nome: string
}

export interface ItemPendente {
  chave: string
  rotulo: string
  essencial: boolean
  campos: CampoDaPendencia[]
  valores: Record<string, Valor>
  situacao: Situacao | null
  origem: 'digitado' | 'anexo' | null
  sugestoes: SugestaoDeAnexo[]
}

export interface GrupoPendente {
  chave: string
  titulo: string
  escala: boolean
  essencial: boolean
  pendentes: number
  itens: ItemPendente[]
}

export interface PendenciasDoLaudo {
  essenciais: { total: number; resolvidos: number }
  grupos: GrupoPendente[]
  escalas_para_adicionar: { chave: string; titulo: string }[]
}

export interface DadoComplementar {
  valor?: Valor
  situacao: Situacao
  origem?: 'digitado' | 'anexo'
  anexo_id?: string | null
}

export const getPendencias = (laudoId: string) => apiGet<PendenciasDoLaudo>(`/reports/${laudoId}/pendencias`)

export const enviarCatalogoDoLaudo = (laudoId: string, catalogo: CatalogoDoProtocolo) =>
  apiPost<PendenciasDoLaudo>(`/reports/${laudoId}/pendencias`, catalogo)

export const marcarEscalasAplicadas = (laudoId: string, escalas: string[]) =>
  apiPut<PendenciasDoLaudo>(`/reports/${laudoId}/escalas-aplicadas`, { escalas })

// null apaga o campo (desfazer).
export const salvarDadosComplementares = (pacienteId: string, campos: Record<string, DadoComplementar | null>) =>
  apiPatch<{ dados: Record<string, DadoComplementar> }>(`/patients/${pacienteId}/dados-complementares`, { campos })
