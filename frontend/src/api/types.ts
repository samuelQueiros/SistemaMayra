export interface Psychologist {
  id: string
  name: string
  email: string
  professional_registration: string | null
}

export interface Patient {
  id: string
  name: string
  birth_date: string
  notes: string | null
  sex: string | null
  school_info: string | null
}

export interface PatientPhoto {
  id: string
  file_path: string
  caption: string | null
  created_at: string
}

export type FieldType = 'scale' | 'boolean' | 'select' | 'text'

export interface TemplateField {
  key: string
  label: string
  type: FieldType
  min?: number | null
  max?: number | null
  options?: string[] | null
  weight: number
}

export interface AgeBracket {
  label: string
  max_age_months: number
  fields: TemplateField[]
}

export interface TemplateArea {
  key: string
  label: string
  fields?: TemplateField[] | null
  age_brackets?: AgeBracket[] | null
}

export type ComparisonOperator = 'gte' | 'gt' | 'lte' | 'lt' | 'eq'

export interface ClassificationRange {
  label: string
  // sum_threshold / age_equivalent_percentage: faixa numérica.
  min?: number | null
  max?: number | null
  // count_threshold: classifica uma área específica por contagem.
  area?: string | null
  minimum_count?: number | null
  comparison?: ComparisonOperator | null
}

export interface TemplateSchemaJSON {
  name: string
  rule_type: 'sum_threshold' | 'count_threshold' | 'age_equivalent_percentage'
  areas: TemplateArea[]
  classification_ranges: ClassificationRange[]
  chart: { type: 'bar' | 'radar' | 'pie'; group_by: string; compare_to?: string | null }
  target_values?: string[] | null
  // Só para rule_type "age_equivalent_percentage": peso numérico de cada
  // resposta possível (ex.: {"sim": 1.0, "as_vezes": 0.5, "nao": 0.2}).
  item_scoring?: Record<string, number> | null
}

export interface ReportTemplate {
  id: string
  name: string
  version: number
  schema_json: TemplateSchemaJSON
}

export type AreaAnswers = Record<string, string | number | boolean>
// Áreas no formato "age_equivalent_percentage" (Portage) aninham as
// respostas mais um nível, por faixa etária: area -> faixa -> campo.
export type Answers = Record<string, AreaAnswers | Record<string, AreaAnswers>>

export interface AgeEquivalentAreaResult {
  developmental_age_months: number
  developmental_age_label: string
  percentage: number
  classification: string | null
}

export interface ComputedResult {
  scores?: Record<string, number>
  total?: number
  classification?: string | null
  classifications?: Record<string, string | null>
  // Só presente quando o template usa rule_type "age_equivalent_percentage".
  areas?: Record<string, AgeEquivalentAreaResult>
  chronological_age_months?: number
}

export interface DiagnosticHypothesis {
  label: string
  cid?: string | null
  // Só a hipótese marcada como selecionada aparece no PDF final.
  selected?: boolean
}

export interface ClinicalSections {
  anamnese?: string | null
  historico_desenvolvimento?: string | null
  encaminhamento_queixas?: string | null
  metodologia?: string | null
  estudo_de_caso?: string | null
  plano_intervencao?: string | null
  encaminhamentos?: string[] | null
  consideracoes_finais?: string | null
  diagnostic_hypotheses?: DiagnosticHypothesis[] | null
}

export interface CidCode {
  label: string
  cid: string
}

export interface Report {
  id: string
  patient_id: string
  template_id: string
  answers_json: Answers
  computed_json: ComputedResult | null
  generated_text: string | null
  pdf_path: string | null
  template_name_override: string | null
  classification_override: string | null
  clinical_sections_json: ClinicalSections | null
  created_at: string
}

export interface ConsolidatedReport {
  id: string
  patient_id: string
  report_ids: string[]
  generated_text: string
  created_at: string
}

export interface StatsByTemplate {
  template_name: string
  count: number
}

export interface StatsSummary {
  total_patients: number
  total_reports: number
  reports_last_30_days: number
  reports_by_template: StatsByTemplate[]
}

export interface ReportChangeLog {
  id: string
  field: string
  old_value: string | null
  new_value: string | null
  created_at: string
  psychologist_name: string
}
