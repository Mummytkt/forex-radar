'use client'
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { API_BASE } from './api'

export interface User {
  id: number
  email: string
  name: string
  role: 'OWNER' | 'SUBSCRIBER'
  plan: string
  created_at?: string
  last_login_at?: string
  plan_expires_at?: string
}

interface AuthCtx {
  user: User | null
  token: string | null
  authEnabled: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  loading: boolean
}

const Auth = createContext<AuthCtx>({
  user: null, token: null, authEnabled: false,
  login: async () => {}, logout: () => {}, refresh: async () => {},
  loading: true,
})

const TOKEN_KEY = 'mbp_token'
const NO_AUTH_PATHS = ['/login', '/join', '/', '/signup', '/checkout', '/forgot', '/reset', '/claim',
  '/terms', '/privacy', '/refunds', '/risk']

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [authEnabled, setAuthEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  const verifyToken = useCallback(async (t: string): Promise<boolean> => {
    try {
      const r = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!r.ok) throw new Error('invalid')
      const u = await r.json()
      setUser(u)
      setToken(t)
      return true
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      setUser(null)
      setToken(null)
      return false
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      try {
        const sr = await fetch(`${API_BASE}/api/auth/status`)
        const status = await sr.json()
        setAuthEnabled(status.enabled)
        if (status.enabled) {
          const t = localStorage.getItem(TOKEN_KEY)
          if (t) await verifyToken(t)
        }
      } catch {
        // API not ready yet
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [verifyToken])

  // Guard: redirect to /login when auth is enabled and user is not authenticated
  useEffect(() => {
    if (loading) return
    if (!authEnabled) return
    if (NO_AUTH_PATHS.some(p => pathname === p || pathname.startsWith(p + '?') || pathname.startsWith(p + '/'))) return
    if (!user) router.replace('/login')
  }, [loading, authEnabled, user, pathname, router])

  const login = async (email: string, password: string) => {
    const r = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!r.ok) {
      const err = await r.json()
      throw new Error(err.detail || 'Login failed')
    }
    const { token: t, user: u } = await r.json()
    localStorage.setItem(TOKEN_KEY, t)
    setToken(t)
    setUser(u)
    router.replace('/dashboard')
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    router.replace('/login')
  }

  const refresh = async () => {
    const t = token ?? localStorage.getItem(TOKEN_KEY)
    if (t) await verifyToken(t)
  }

  return (
    <Auth.Provider value={{ user, token, authEnabled, login, logout, refresh, loading }}>
      {children}
    </Auth.Provider>
  )
}

export const useAuth = () => useContext(Auth)
