import { apiGet, apiPatch, apiPost, apiPut, downloadGet } from './client'
import type { Answers, CidCode, ClinicalSections, Report, ReportChangeLog, ReportResumo } from './types'

export const createReport = (patientId: string, templateId: string, answers: Answers) =>
  apiPost<Report>(`/patients/${patientId}/reports`, { template_id: templateId, answers })

export const listReports = (patientId: string) => apiGet<ReportResumo[]>(`/patients/${patientId}/reports`)

export const getReportResumo = (id: string) => apiGet<ReportResumo>(`/reports/${id}/resumo`)

export const getReport = (id: string) => apiGet<Report>(`/reports/${id}`)

export const generateReportText = (reportId: string) =>
  apiPost<Report>(`/reports/${reportId}/generate-text`, {})

export const updateReportText = (reportId: string, generatedText: string) =>
  apiPut<ReportResumo>(`/reports/${reportId}/text`, { generated_text: generatedText })

export const updateReportEdit = (
  reportId: string,
  data: { template_name_override?: string; classification_override?: string },
) => apiPatch<ReportResumo>(`/reports/${reportId}`, data)

export const getReportLogs = (reportId: string) =>
  apiGet<ReportChangeLog[]>(`/reports/${reportId}/logs`)

export const downloadReportPdf = (reportId: string, fileName: string) => downloadGet(`/reports/${reportId}/pdf`, fileName)

export const downloadReportDocx = (reportId: string, fileName: string) =>
  downloadGet(`/reports/${reportId}/docx`, fileName)

export const updateClinicalSections = (reportId: string, data: ClinicalSections) =>
  apiPatch<ReportResumo>(`/reports/${reportId}/clinical-sections`, data)

export const listCidCodes = () => apiGet<CidCode[]>('/cid-codes')


export interface LogDeEdicao {
  id: string
  field: string
  old_value: string | null
  new_value: string | null
  created_at: string
  psychologist_name: string
  report_id: string
  report_created_at: string
  patient_id: string
  patient_name: string
  template_name: string
}

export const listAllLogs = (patientId?: string) =>
  apiGet<LogDeEdicao[]>(`/logs${patientId ? `?patient_id=${patientId}` : ''}`)
