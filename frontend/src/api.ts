import axios from 'axios'
import type { AnalyticsOverview, Dashboard, Inspection, KnowledgeDocument, TraceStep } from './types'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', timeout: 60_000 })
export const API_KEY_STORAGE = 'campus-safety-api-key'

export function getApiKey(): string {
  return sessionStorage.getItem(API_KEY_STORAGE)?.trim() || ''
}

export function saveApiKey(value: string): void {
  const key = value.trim()
  if (key) sessionStorage.setItem(API_KEY_STORAGE, key)
  else sessionStorage.removeItem(API_KEY_STORAGE)
}

api.interceptors.request.use((config) => {
  const key = getApiKey()
  if (key) config.headers.set('X-API-Key', key)
  return config
})

export function inspectionStreamUrl(id: string): string {
  const base = String(api.defaults.baseURL || '/api/v1').replace(/\/$/, '')
  const key = getApiKey()
  const query = key ? `?api_key=${encodeURIComponent(key)}` : ''
  return `${base}/inspections/${encodeURIComponent(id)}/stream${query}`
}

export const getDashboard = async () => (await api.get<Dashboard>('/dashboard')).data
export const getAnalyticsOverview = async () => (await api.get<AnalyticsOverview>('/analytics/overview')).data
export const getInspections = async (params: Record<string, unknown> = {}) =>
  (await api.get<{ items: Inspection[]; total: number }>('/inspections', { params })).data
export const getInspection = async (id: string) => (await api.get<Inspection>(`/inspections/${id}`)).data
export const executeInspection = async (id: string) => (await api.post(`/inspections/${id}/execute`)).data
export const getTrace = async (id: string) =>
  (await api.get<{ steps: TraceStep[] }>(`/inspections/${id}/trace`)).data.steps
export const getKnowledgeDocuments = async () =>
  (await api.get<{ items: KnowledgeDocument[] }>('/knowledge/documents')).data.items

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : error.message
  }
  return error instanceof Error ? error.message : '操作失败'
}
