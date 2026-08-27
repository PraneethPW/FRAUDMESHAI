import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { TokenPair, User } from '../types'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  setSession: (session: TokenPair) => void
  clearSession: () => void
}

export const useAuth = create<AuthState>()(persist((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setSession: (session) => set({ accessToken: session.access_token, refreshToken: session.refresh_token, user: session.user }),
  clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
}), { name: 'fraudmesh-session' }))

