'use client'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher } from '@/lib/api'
import type { InstrumentOverview } from '@/lib/types'
import { stateLabel, timeAgo, directionColor } from '@/lib/utils'
import clsx from 'clsx'

const CATEGORIES = ['Major', 'EUR Cross', 'GBP Cross', 'Commodity Cross', 'Metal', 'Crypto']

const stateChip: Record<string, { bg: string; text: string }> = {
  IDLE: { bg: '#25263622', text: '#7880A0' },
  BREAKOUT_ACTIVE: { bg: '#6366F122', text: '#818CF8' },
  RETEST_IN_PROGRESS: { bg: '#F59E0B22', text: '#FCD34D' },
}

export default function InstrumentsPage() {
  const { data: instruments } = useSWR<InstrumentOverview[]>('/api/overview', fetcher, { refreshInterval: 30000 })

  const byCategory = CATEGORIES.reduce<Record<string, InstrumentOverview[]>>((acc, cat) => {
    acc[cat] = (instruments ?? []).filter(i => i.category === cat)
    return acc
  }, {})

  const active = (instruments ?? []).filter(i => i.state !== 'IDLE').length
  const retest = (instruments ?? []).filter(i => i.state === 'RETEST_IN_PROGRESS').length

  return (
    <>
      <TopBar title="Instruments" />
      <main className="flex-1 p-6 space-y-6">
        {/* Summary chips */}
        <div className="flex items-center gap-3 text-xs">
          <span className="px-3 py-1.5 rounded-full"
            style={{ background: 'var(--card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
            {instruments?.length ?? '—'} total
          </span>
          <span className="px-3 py-1.5 rounded-full"
            style={{ background: '#6366F122', color: '#818CF8' }}>
            {active} active
          </span>
          <span className="px-3 py-1.5 rounded-full"
            style={{ background: '#F59E0B22', color: '#FCD34D' }}>
            {retest} in retest
          </span>
        </div>

        {CATEGORIES.map(cat => {
          const items = byCategory[cat]
          if (!items?.length) return null
          return (
            <section key={cat}>
              <h2 className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-secondary)' }}>{cat}</h2>
              <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                {items.map((inst, i) => {
                  const chip = stateChip[inst.state]
                  return (
                    <div key={inst.instrument}
                      className={clsx('flex items-center gap-4 px-4 py-3', i > 0 && 'border-t')}
                      style={i > 0 ? { borderColor: 'var(--border)', background: 'var(--card)' } : { background: 'var(--card)' }}>
                      {/* Name */}
                      <span className="font-semibold text-sm w-24 flex-shrink-0"
                        style={{ color: 'var(--text-primary)' }}>{inst.instrument}</span>

                      {/* State badge */}
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium w-36 text-center flex-shrink-0"
                        style={{ background: chip.bg, color: chip.text }}>
                        {inst.state === 'RETEST_IN_PROGRESS' && <span className="inline-block w-1.5 h-1.5 rounded-full pulse mr-1.5 align-middle" style={{ background: chip.text }} />}
                        {stateLabel(inst.state)}
                      </span>

                      {/* Direction */}
                      <span className={clsx('text-xs flex items-center gap-1 w-24 flex-shrink-0',
                        inst.direction === 'BULLISH' ? 'text-green-400' :
                          inst.direction === 'BEARISH' ? 'text-red-400' : 'opacity-40 text-gray-400')}>
                        {inst.direction === 'BULLISH' ? <TrendingUp size={12} /> :
                          inst.direction === 'BEARISH' ? <TrendingDown size={12} /> : <Minus size={12} />}
                        {inst.direction ?? 'Neutral'}
                      </span>

                      {/* Level */}
                      <span className="text-xs font-mono flex-shrink-0 w-24"
                        style={{ color: inst.breakout_level ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {inst.breakout_level?.toFixed(5) ?? '—'}
                      </span>

                      {/* Sources */}
                      <span className="text-xs flex-shrink-0 w-20 text-right ml-auto"
                        style={{ color: 'var(--text-secondary)' }}>
                        {inst.active_sources_count > 0 ? `${inst.active_sources_count} sources` : '—'}
                      </span>

                      {/* Updated */}
                      <span className="text-xs text-right flex-shrink-0 hidden xl:block w-28"
                        style={{ color: 'var(--text-secondary)' }}>
                        {timeAgo(inst.last_updated)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </section>
          )
        })}
      </main>
    </>
  )
}
