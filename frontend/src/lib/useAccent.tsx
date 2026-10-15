'use client'
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { PALETTE, DEFAULT_ACCENT, applyAccent } from './accent'
import { useTheme } from './theme'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

interface AccentCtx {
  accent: string
  setAccent: (id: string) => Promise<void>
}

const Ctx = createContext<AccentCtx>({ accent: DEFAULT_ACCENT, setAccent: async () => {} })

export function AccentProvider({ children }: { children: ReactNode }) {
  const { theme } = useTheme()
  const [accent, setAccentState] = useState<string>(() => {
    try { return localStorage.getItem('mbp_accent') ?? DEFAULT_ACCENT } catch { return DEFAULT_ACCENT }
  })

  // Apply on mount and whenever theme changes
  useEffect(() => {
    applyAccent(accent, theme as 'dark' | 'light')
  }, [accent, theme])

  // Load from server on mount (syncs across devices)
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
    if (!token) return
    fetch(`${API_BASE}/api/preferences/accent`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.accent_color && PALETTE.some(s => s.id === data.accent_color)) {
          setAccentState(data.accent_color)
        }
      })
      .catch(() => {})
  }, [])

  const setAccent = useCallback(async (id: string) => {
    setAccentState(id)
    applyAccent(id, (document.documentElement.getAttribute('data-theme') ?? 'dark') as 'dark' | 'light')
    const token = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
    if (!token) return
    await fetch(`${API_BASE}/api/preferences/accent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ accent_color: id }),
    }).catch(() => {})
  }, [])

  return <Ctx.Provider value={{ accent, setAccent }}>{children}</Ctx.Provider>
}

export const useAccent = () => useContext(Ctx)
