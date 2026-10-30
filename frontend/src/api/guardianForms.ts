/** Chamadas dos formulários preenchidos pelos responsáveis (`/api/patients/{id}/guardian-forms`). */
import { apiDelete, apiGet, apiPost, apiPostFile } from './client'
import type { GuardianFormSubmission } from './types'

export const listGuardianForms = (patientId: string) =>
  apiGet<GuardianFormSubmission[]>(`/patients/${patientId}/guardian-forms`)

export const createGuardianForm = (
  patientId: string,
  data: {
    kind: string
    respondent_name: string
    respondent_relation?: string
    filled_at: string
    notes?: string
  },
) => apiPost<GuardianFormSubmission>(`/patients/${patientId}/guardian-forms`, data)

export const uploadGuardianFormFile = (patientId: string, submissionId: string, file: File) =>
  apiPostFile<GuardianFormSubmission>(`/patients/${patientId}/guardian-forms/${submissionId}/file`, file)

export const validateGuardianForm = (patientId: string, submissionId: string) =>
  apiPost<GuardianFormSubmission>(`/patients/${patientId}/guardian-forms/${submissionId}/validate`, {})

export const rejectGuardianForm = (patientId: string, submissionId: string) =>
  apiPost<GuardianFormSubmission>(`/patients/${patientId}/guardian-forms/${submissionId}/reject`, {})

export const deleteGuardianForm = (patientId: string, submissionId: string) =>
  apiDelete<void>(`/patients/${patientId}/guardian-forms/${submissionId}`)
