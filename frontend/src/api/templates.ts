/**
 * Chamadas dos modelos do motor de regras (`/api/templates`). O fluxo principal só usa `listTemplates`; os
 * demais vieram do motor antigo.
 */
import { apiGet, apiPost, apiPostFile } from './client'
import type { ReportTemplate, TemplateSchemaJSON } from './types'

export const listTemplates = () => apiGet<ReportTemplate[]>('/templates')

export const getTemplate = (id: string) => apiGet<ReportTemplate>(`/templates/${id}`)

export interface TemplateImportResult {
  draft_schema_json: TemplateSchemaJSON
  validation_errors: string[]
}

export const importTemplateFromDocument = (file: File) =>
  apiPostFile<TemplateImportResult>('/templates/import', file)

export const createTemplate = (name: string, schema_json: TemplateSchemaJSON, version = 1) =>
  apiPost<ReportTemplate>('/templates', { name, version, schema_json })
