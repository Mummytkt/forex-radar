import type { InstrumentOverview, Stats, AlertsPage, InstrumentDetail } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://forex-radar.fly.dev'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 30 } })
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const fetcher = (url: string) =>
  fetch(`${BASE}${url}`).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })

export const api = {
  overview: () => get<InstrumentOverview[]>('/api/overview'),
  stats: () => get<Stats>('/api/stats'),
  alerts: (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return get<AlertsPage>(`/api/alerts${qs}`)
  },
  instrument: (slug: string) => get<InstrumentDetail>(`/api/instrument/${slug}`),
}
