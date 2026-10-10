'use client'
import { useState } from 'react'
import { ChevronDown, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { InstrumentOverview } from '@/lib/types'
import { timeAgo, stateLabel } from '@/lib/utils'

const STATE_STYLES: Record<string, { border: string; badge: string; badgeText: string }> = {
  IDLE:                { border: 'var(--border)', badge: 'var(--border)', badgeText: 'var(--text-secondary)' },
  BREAKOUT_ACTIVE:     { border: 'var(--accent)', badge: 'var(--accent-bg)', badgeText: 'var(--accent-hover)' },
  RETEST_IN_PROGRESS:  { border: 'var(--warning)', badge: 'var(--warning-bg)', badgeText: 'var(--warning)' },
}

export default function InstrumentCard({ d }: { d: InstrumentOverview }) {
  const [open, setOpen] = useState(false)
  const s = STATE_STYLES[d.state]

  return (
    <div
      onClick={() => setOpen(o => !o)}
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderLeft: `3px solid ${s.border}`,
        borderRadius: 10,
        cursor: 'pointer',
        transition: 'background 0.12s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--card-hover)'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'var(--card)'}
    >
      <div style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>{d.instrument}</span>
              <span style={{
                fontSize: 10, padding: '1px 7px', borderRadius: 99,
                background: 'var(--border)', color: 'var(--text-secondary)', fontWeight: 500,
              }}>{d.category}</span>
            </div>
            {d.direction ? (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 5, marginTop: 5, fontSize: 13, fontWeight: 600,
                color: d.direction === 'BULLISH' ? 'var(--bullish)' : 'var(--bearish)',
              }}>
                {d.direction === 'BULLISH' ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                {d.direction === 'BULLISH' ? 'Bullish' : 'Bearish'}
                {d.breakout_level && (
                  <span style={{ fontWeight: 400, fontSize: 12, color: 'var(--text-secondary)', marginLeft: 3 }}>
                    @ {d.breakout_level.toFixed(5)}
                  </span>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 5, fontSize: 12, color: 'var(--text-muted)' }}>
                <Minus size={12} /> No active bias
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 7, flexShrink: 0 }}>
            <span className="badge" style={{ background: s.badge, color: s.badgeText }}>
              {d.state === 'RETEST_IN_PROGRESS' && (
                <span className="pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: s.badgeText, display: 'inline-block' }} />
              )}
              {stateLabel(d.state)}
            </span>
            <ChevronDown size={13} style={{ color: 'var(--text-muted)', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 14, marginTop: 10, fontSize: 11, color: 'var(--text-secondary)' }}>
          {d.active_sources_count > 0 && <span>{d.active_sources_count} source{d.active_sources_count !== 1 ? 's' : ''}</span>}
          <span>Updated {timeAgo(d.last_updated)}</span>
          {d.last_alert_at && <span>Alert {timeAgo(d.last_alert_at)}</span>}
        </div>
      </div>

      {open && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', fontSize: 12 }} className="fade-up">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {[
              ['State', stateLabel(d.state)],
              d.breakout_level ? ['Broken level', d.breakout_level.toFixed(5)] : null,
              d.breakout_ts ? ['Breakout candle', new Date(d.breakout_ts).toLocaleDateString('en-GB', { timeZone: 'UTC' })] : null,
              d.last_alert_at ? ['Last alert', timeAgo(d.last_alert_at)] : null,
            ].filter((x): x is [string, string] => x !== null).map(([k, v]) => (
              <div key={k as string} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{v}</span>
              </div>
            ))}
            {!d.last_alert_at && (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 4 }}>No alerts fired yet</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
