import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { create } from 'zustand'
import { api, refreshSession, WS_URL } from './api'
import { useAuth } from '../store/auth'

export const useLive = create<{ connected: boolean }>(() => ({ connected: false }))
export function useWorkspaceStream() {
  const client = useQueryClient()
  const token = useAuth((state) => state.accessToken)
  useEffect(() => {
    if (!token) return
    let active = true, socket: WebSocket | undefined, retry: ReturnType<typeof setTimeout> | undefined
    let timer: ReturnType<typeof setTimeout> | undefined, attempts = 0
    const dirty = new Set<string>()
    const flush = () => {
      for (const key of dirty) void client.invalidateQueries({ queryKey: [key] })
      dirty.clear(); timer = undefined
    }
    const schedule = (keys: string[]) => {
      keys.forEach((key) => dirty.add(key))
      timer ??= setTimeout(flush, 1500)
    }
    const connect = () => {
      if (!active) return
      socket = new WebSocket(`${WS_URL}?token=${encodeURIComponent(useAuth.getState().accessToken || '')}`)
      socket.onopen = () => { attempts = 0; useLive.setState({ connected: true }); void client.invalidateQueries() }
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as { event: string }
          if (message.event === 'heartbeat') { socket?.send('pong'); return }
          if (message.event.startsWith('transaction.')) schedule(['transactions', 'overview', 'dashboard', 'graph', 'dashboard-graph'])
          if (message.event.startsWith('fraud.')) schedule(['alerts', 'alert', 'rings', 'notifications', 'dashboard', 'overview'])
          if (message.event.startsWith('case.')) schedule(['case', 'cases', 'alerts', 'notifications', 'dashboard', 'overview'])
          if (message.event.startsWith('model.')) schedule(['model-runs', 'admin', 'dashboard', 'overview'])
          if (message.event.startsWith('simulation.')) schedule(['simulation'])
        } catch { /* Ignore malformed frames; REST reconciliation remains available. */ }
      }
      socket.onclose = (event) => {
        useLive.setState({ connected: false })
        if (!active) return
        if (event.code === 4401) {
          void refreshSession().then(() => { if (active) retry = setTimeout(connect, 250) }).catch(() => { if (active) retry = setTimeout(connect, 15000) })
        } else retry = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempts++))
      }
      socket.onerror = () => socket?.close()
    }
    connect()
    const fallback = setInterval(() => {
      if (!document.hidden && !useLive.getState().connected) { void api.get('/users/me').catch(()=>undefined); void client.invalidateQueries() }
    }, 30000)
    return () => { active = false; clearTimeout(retry); clearTimeout(timer); clearInterval(fallback); socket?.close(); useLive.setState({ connected: false }) }
  }, [client, token])
}
