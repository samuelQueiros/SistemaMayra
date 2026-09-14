import { apiDelete, apiGet, apiPost, apiPostFile, getToken } from './client'
import type { Patient, PatientPhoto } from './types'

export const listPatients = () => apiGet<Patient[]>('/patients')

export const createPatient = (data: {
  name: string
  birth_date: string
  notes?: string
  sex?: string
  school_info?: string
}) => apiPost<Patient>('/patients', data)

export const getPatient = (id: string) => apiGet<Patient>(`/patients/${id}`)

export const listPatientPhotos = (patientId: string) =>
  apiGet<PatientPhoto[]>(`/patients/${patientId}/photos`)

export const uploadPatientPhoto = (patientId: string, file: File) =>
  apiPostFile<PatientPhoto>(`/patients/${patientId}/photos`, file)

export const deletePatientPhoto = (patientId: string, photoId: string) =>
  apiDelete<void>(`/patients/${patientId}/photos/${photoId}`)

// A rota de arquivo exige autenticação (Bearer token), então uma tag <img
// src="..."> comum não funciona — busca o arquivo como blob autenticado e
// devolve uma URL de objeto local para usar no src.
export async function fetchPatientPhotoUrl(patientId: string, photoId: string): Promise<string> {
  const token = getToken()
  const response = await fetch(`/api/patients/${patientId}/photos/${photoId}/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`Não foi possível carregar a foto (erro ${response.status}).`)
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
