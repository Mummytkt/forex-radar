'use client'
import useSWR from 'swr'
import { Activity, Zap, Bell, BarChart2 } from 'lucide-react'
import TopBar from '@/components/TopBar'
import StatCard from '@/components/StatCard'
import InstrumentCard from '@/components/InstrumentCard'
import { fetcher } from '@/lib/api'
import type { InstrumentOverview, Stats } from '@/lib/types'

const STATE_ORDER = { RETEST_IN_PROGRESS: 0, BREAKOUT_ACTIVE: 1, IDLE: 2 }

const CATEGORY_ORDER = ['Major', 'EUR Cross', 'GBP Cross', 'Commodity Cross', 'Metal', 'Crypto']

export default function Dashboard() {
  const { data: instruments } = useSWR<InstrumentOverview[]>('/api/overview', fetcher, { refreshInterval: 30000 })
  const { data: stats } = useSWR<Stats>('/api/stats', fetcher, { refreshInterval: 30000 })

  const sorted = [...(instruments ?? [])].sort((a, b) => {
    const sd = STATE_ORDER[a.state] - STATE_ORDER[b.state]
    if (sd !== 0) return sd
    return a.instrument.localeCompare(b.instrument)
  })

  const byCategory = CATEGORY_ORDER.reduce<Record<string, InstrumentOverview[]>>((acc, cat) => {
    acc[cat] = sorted.filter(i => i.category === cat)
    return acc
  }, {})

  return (
    <>
      <TopBar title="Dashboard" />
      <main className="flex-1 p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Instruments Monitored" value={stats?.total_instruments ?? '—'} icon={BarChart2} />
          <StatCard label="Active Breakouts" value={stats?.active_breakouts ?? '—'} icon={Activity}
            accent="var(--accent)" sub="Bias setups live" />
          <StatCard label="Retests In Progress" value={stats?.retests_in_progress ?? '—'} icon={Zap}
            accent="var(--retest)" sub="Awaiting H4 confirm" />
          <StatCard label="Total Alerts Fired" value={stats?.total_alerts ?? '—'} icon={Bell}
            accent="var(--bullish)" sub={stats ? `${stats.alerts_today} today` : undefined} />
        </div>

        {/* Instrument grid by category */}
        {!instruments && (
          <div className="text-center py-16 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Loading instruments…
          </div>
        )}

        {instruments && CATEGORY_ORDER.map(cat => {
          const items = byCategory[cat]
          if (!items?.length) return null
          return (
            <section key={cat}>
              <h2 className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-secondary)' }}>
                {cat} <span className="ml-1 opacity-50">({items.length})</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {items.map(inst => <InstrumentCard key={inst.instrument} d={inst} />)}
              </div>
            </section>
          )
        })}
      </main>
    </>
  )
}
