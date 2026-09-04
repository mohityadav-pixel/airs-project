import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { api, getToken, setToken } from './api'
import type { Role, User } from './types'

const RANK: Record<Role, number> = { citizen: 0, analyst: 1, official: 2, admin: 3 }

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (body: { email: string; full_name: string; password: string
                     home_city_slug?: string; sensitivity_group?: string }) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  hasRole: (minimum: Role) => boolean
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  const refresh = useCallback(async () => {
    if (!getToken()) { setUser(null); setLoading(false); return }
    try {
      setUser(await api.me())
    } catch {
      setToken(null); setUser(null)     // expired or revoked
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const value = useMemo<AuthValue>(() => ({
    user, loading,
    login: async (email, password) => {
      const { access_token } = await api.login(email, password)
      setToken(access_token)
      setUser(await api.me())
    },
    register: async (body) => {
      const { access_token } = await api.register(body)
      setToken(access_token)
      setUser(await api.me())
    },
    logout: () => { setToken(null); setUser(null) },
    refresh,
    hasRole: (minimum) => Boolean(user && RANK[user.role] >= RANK[minimum]),
  }), [user, loading, refresh])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
