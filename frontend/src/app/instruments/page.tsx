'use client'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, Clock } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import type { InstrumentOverview } from '@/lib/types'

const CATEGORIES = ['Major', 'EUR Cross', 'GBP Cross', 'Commodity Cross', 'Metal', 'Energy', 'Index', 'Crypto']

// State badge: includes the setup direction as a hint (not confirmed bias)
function StateBadge({ state, direction }: { state: string; direction: string | null }) {
  const dir = direction === 'BULLISH' ? '↑' : direction === 'BEARISH' ? '↓' : ''

  if (state === 'IDLE') {
    return (
      <span className="badge" style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}>
        Idle
      </span>
    )
  }
  if (state === 'RETEST_IN_PROGRESS') {
    return (
      <span className="badge" style={{ background: 'var(--warning-bg)', color: 'var(--warning)' }}>
        <span className="pulse" style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--warning)', display: 'inline-block' }} />
        {dir} Retesting
      </span>
    )
  }
  // BREAKOUT_ACTIVE
  return (
    <span className="badge" style={{ background: 'var(--accent-bg)', color: 'var(--accent-hover)' }}>
      {dir} Setup Active
    </span>
  )
}

// Confirmed bias: only shows after a full alert has fired (Daily + H4 aligned)
function ConfirmedBias({ inst }: { inst: InstrumentOverview }) {
  if (inst.last_alert_direction) {
    const bull = inst.last_alert_direction === 'BULLISH'
    return (
      <div>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 600,
          color: bull ? 'var(--bullish)' : 'var(--bearish)',
        }}>
          {bull ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {bull ? 'Bullish' : 'Bearish'}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          Confirmed {timeAgo(inst.last_alert_at)}
        </div>
      </div>
    )
  }

  if (inst.state === 'IDLE') {
    return <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>—</span>
  }

  // Setup active or retesting but no alert yet
  const dir = inst.direction === 'BULLISH' ? '↑' : inst.direction === 'BEARISH' ? '↓' : ''
  return (
    <div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 5 }}>
        <Clock size={11} />
        {dir} Awaiting H4 confirm
      </div>
    </div>
  )
}

export default function InstrumentsPage() {
  const { data: instruments } = useSWR<InstrumentOverview[]>('/api/overview', fetcher, { refreshInterval: 30000 })

  const byCategory = CATEGORIES.reduce<Record<string, InstrumentOverview[]>>((acc, cat) => {
    acc[cat] = (instruments ?? []).filter(i => i.category === cat)
      .sort((a, b) => {
        const o = { RETEST_IN_PROGRESS: 0, BREAKOUT_ACTIVE: 1, IDLE: 2 }
        return o[a.state] - o[b.state]
      })
    return acc
  }, {})

  const active = (instruments ?? []).filter(i => i.state !== 'IDLE').length
  const confirmed = (instruments ?? []).filter(i => i.last_alert_direction != null).length
  const retest = (instruments ?? []).filter(i => i.state === 'RETEST_IN_PROGRESS').length
  const total = instruments?.length ?? 0

  return (
    <>
      <TopBar title="Markets" subtitle={`${total} instruments under surveillance`} />
      <main className="page-padded" style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Summary chips */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: `${total} total`, bg: 'var(--card)', color: 'var(--text-secondary)', border: 'var(--border)' },
            { label: `${active} setups active`, bg: 'var(--accent-bg)', color: 'var(--accent-hover)', border: 'transparent' },
            { label: `${retest} retesting`, bg: 'var(--warning-bg)', color: 'var(--warning)', border: 'transparent' },
            { label: `${confirmed} confirmed bias`, bg: 'var(--bullish-bg)', color: 'var(--bullish)', border: 'transparent' },
          ].map(({ label, bg, color, border }) => (
            <span key={label} style={{ padding: '5px 14px', borderRadius: 99, fontSize: 12, fontWeight: 500, background: bg, color, border: `1px solid ${border}` }}>
              {label}
            </span>
          ))}
        </div>

        {/* Legend */}
        <div style={{
          padding: '12px 16px', borderRadius: 10, fontSize: 12,
          background: 'var(--card)', border: '1px solid var(--border)',
          color: 'var(--text-secondary)', lineHeight: 1.7,
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>How to read:</strong>
          {' '}<span style={{ color: 'var(--accent-hover)' }}>Setup Active</span> = Daily breakout detected, engine watching for a retest of a key reaction level.
          {' '}<span style={{ color: 'var(--warning)' }}>Retesting</span> = price is touching a reaction zone, H4 confirmation pending.
          {' '}<strong style={{ color: 'var(--bullish)' }}>Confirmed Bias</strong> = all 4 conditions met — Daily breakout → reaction source touched → H4 closed beyond its formation. An alert fired.
        </div>

        {CATEGORIES.map(cat => {
          const items = byCategory[cat]
          if (!items?.length) return null
          return (
            <section key={cat}>
              <h2 style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-secondary)', marginBottom: 10 }}>
                {cat} <span style={{ opacity: 0.5 }}>({items.length})</span>
              </h2>
              <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                <div className="table-wrap">
                  <table className="data-table" style={{ minWidth: 600 }}>
                    <thead>
                      <tr>
                        <th>Instrument</th>
                        <th>Setup State</th>
                        <th>Confirmed Bias</th>
                        <th>Breakout Level</th>
                        <th>Sources</th>
                        <th>Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map(inst => (
                        <tr key={inst.instrument}>
                          <td>
                            <span style={{ fontWeight: 600, fontSize: 13 }}>{inst.instrument}</span>
                          </td>
                          <td>
                            <StateBadge state={inst.state} direction={inst.direction} />
                          </td>
                          <td>
                            <ConfirmedBias inst={inst} />
                          </td>
                          <td>
                            <span style={{ fontFamily: 'monospace', fontSize: 12, color: inst.breakout_level ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                              {inst.breakout_level?.toFixed(5) ?? '—'}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: 12, color: inst.active_sources_count > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                              {inst.active_sources_count > 0 ? inst.active_sources_count : '—'}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{timeAgo(inst.last_updated)}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )
        })}
      </main>
    </>
  )
}
