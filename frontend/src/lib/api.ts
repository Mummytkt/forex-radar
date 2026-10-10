import type { InstrumentOverview, Stats, AlertsPage, InstrumentDetail } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://forex-radar.fly.dev'

export const API_BASE = BASE

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 30 } })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

function authHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {}
  const t = localStorage.getItem('mbp_token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export const fetcher = (url: string) =>
  fetch(`${BASE}${url}`, { headers: authHeaders() }).then(r => {
    if (r.status === 401 && typeof window !== 'undefined') {
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })

export const api = {
  overview: () => get<InstrumentOverview[]>('/api/overview'),
  stats: () => get<Stats>('/api/stats'),
  alerts: (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return get<AlertsPage>(`/api/alerts${qs}`)
  },
  instrument: (slug: string) => get<InstrumentDetail>(`/api/instrument/${slug}`),
}
