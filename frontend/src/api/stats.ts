/** Números de uso do painel (`/api/stats/summary`). */
import { apiGet } from './client'
import type { StatsSummary } from './types'

export const getStatsSummary = () => apiGet<StatsSummary>('/stats/summary')
