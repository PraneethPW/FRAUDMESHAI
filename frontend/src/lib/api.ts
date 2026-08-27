import axios from 'axios'
import { useAuth } from '../store/auth'
import type { TokenPair } from '../types'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws'

export const api = axios.create({ baseURL: API_URL, timeout: 20000 })

api.interceptors.request.use((config) => {
  const token = useAuth.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string> | null = null
api.interceptors.response.use((response) => response, async (error: unknown) => {
  if (!axios.isAxiosError(error) || error.response?.status !== 401 || error.config?.url?.includes('/auth/')) return Promise.reject(error)
  const state = useAuth.getState()
  if (!state.refreshToken) {
    state.clearSession()
    return Promise.reject(error)
  }
  refreshing ??= axios.post<TokenPair>(`${API_URL}/auth/refresh`, { refresh_token: state.refreshToken }).then(({ data }) => {
    state.setSession(data)
    return data.access_token
  }).finally(() => { refreshing = null })
  try {
    const token = await refreshing
    const config = error.config
    if (config) {
      config.headers.Authorization = `Bearer ${token}`
      return api.request(config)
    }
  } catch {
    state.clearSession()
  }
  return Promise.reject(error)
})

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (typeof detail?.message === 'string') return detail.message
    if (!error.response) return 'FraudMesh API is offline. Start the backend and try again.'
  }
  return error instanceof Error ? error.message : 'Something went wrong'
}

