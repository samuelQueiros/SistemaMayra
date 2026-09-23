import { apiGet, apiPatch, apiPost, apiPut, downloadBlob, downloadGet } from './client'
import type { Answers, CidCode, ClinicalSections, ConsolidatedReport, Report, ReportChangeLog } from './types'

export const createReport = (patientId: string, templateId: string, answers: Answers) =>
  apiPost<Report>(`/patients/${patientId}/reports`, { template_id: templateId, answers })

export const listReports = (patientId: string) => apiGet<Report[]>(`/patients/${patientId}/reports`)

export const getReport = (id: string) => apiGet<Report>(`/reports/${id}`)

export const generateReportText = (reportId: string) =>
  apiPost<Report>(`/reports/${reportId}/generate-text`, {})

export const updateReportText = (reportId: string, generatedText: string) =>
  apiPut<Report>(`/reports/${reportId}/text`, { generated_text: generatedText })

export const updateReportEdit = (
  reportId: string,
  data: { template_name_override?: string; classification_override?: string },
) => apiPatch<Report>(`/reports/${reportId}`, data)

export const getReportLogs = (reportId: string) =>
  apiGet<ReportChangeLog[]>(`/reports/${reportId}/logs`)

export const downloadReportPdf = (reportId: string, fileName: string) => downloadGet(`/reports/${reportId}/pdf`, fileName)

export const downloadReportDocx = (reportId: string, fileName: string) =>
  downloadGet(`/reports/${reportId}/docx`, fileName)

export const downloadConsolidatedPdf = (patientId: string, reportIds: string[], fileName: string) =>
  downloadBlob(`/patients/${patientId}/consolidated-pdf`, { report_ids: reportIds }, fileName)

export const updateClinicalSections = (reportId: string, data: ClinicalSections) =>
  apiPatch<Report>(`/reports/${reportId}/clinical-sections`, data)

export const listCidCodes = () => apiGet<CidCode[]>('/cid-codes')

export const listConsolidatedReports = (patientId: string) =>
  apiGet<ConsolidatedReport[]>(`/patients/${patientId}/consolidated-reports`)

export const downloadSavedConsolidatedPdf = (consolidatedReportId: string, fileName: string) =>
  downloadGet(`/consolidated-reports/${consolidatedReportId}/pdf`, fileName)
