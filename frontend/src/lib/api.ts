import axios from 'axios'
import { useAuth } from '../store/auth'
import type { TokenPair } from '../types'

export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')
export const WS_URL = import.meta.env.VITE_WS_URL || `${API_URL.replace(/^http/, 'ws')}/ws`
export const api = axios.create({ baseURL: API_URL, timeout: 20000 })
api.interceptors.request.use((config) => {
  const token = useAuth.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
let refreshing: Promise<string> | null = null
export function refreshSession(): Promise<string> {
  const state = useAuth.getState()
  if (!state.refreshToken) return Promise.reject(new Error('Please sign in again'))
  refreshing ??= axios.post<TokenPair>(`${API_URL}/auth/refresh`, { refresh_token: state.refreshToken }, { timeout: 15000 }).then(({ data }) => {
    // A response from an old session must not log a signed-out user back in.
    if (useAuth.getState().refreshToken !== state.refreshToken) throw new Error('Session changed')
    state.setSession(data)
    return data.access_token
  }).catch((error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && useAuth.getState().refreshToken === state.refreshToken) state.clearSession()
    throw error
  }).finally(() => { refreshing = null })
  return refreshing
}
api.interceptors.response.use((response) => response, async (error: unknown) => {
  if (!axios.isAxiosError(error) || error.response?.status !== 401 || error.config?.url?.includes('/auth/')) return Promise.reject(error)
  const config = error.config as (NonNullable<typeof error.config> & { _retried?: boolean }) | undefined
  if (!config || config._retried) return Promise.reject(error)
  config._retried = true
  try {
    config.headers.Authorization = `Bearer ${await refreshSession()}`
    return api.request(config)
  } catch (refreshError) { return Promise.reject(refreshError) }
})
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (typeof detail?.message === 'string') return detail.message
    if (Array.isArray(detail)) return detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg}`).join('; ')
    if (!error.response) return 'FraudMesh API is temporarily unreachable. Please try again.'
  }
  return error instanceof Error ? error.message : 'Something went wrong'
}
export async function downloadFile(path: string, filename: string) {
  const { data } = await api.get(path, { responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
