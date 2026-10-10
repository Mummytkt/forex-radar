'use client'
import { useState } from 'react'
import { ChevronDown, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'
import type { InstrumentOverview } from '@/lib/types'
import { timeAgo, stateLabel, stateBorder, directionColor, sourceTypeLabel } from '@/lib/utils'

const borderColor: Record<string, string> = {
  IDLE: '#252636',
  BREAKOUT_ACTIVE: '#6366F1',
  RETEST_IN_PROGRESS: '#F59E0B',
}

const badgeStyle: Record<string, { bg: string; text: string }> = {
  IDLE: { bg: '#252636', text: '#7880A0' },
  BREAKOUT_ACTIVE: { bg: '#6366F122', text: '#818CF8' },
  RETEST_IN_PROGRESS: { bg: '#F59E0B22', text: '#FCD34D' },
}

export default function InstrumentCard({ d }: { d: InstrumentOverview }) {
  const [open, setOpen] = useState(false)
  const badge = badgeStyle[d.state]

  return (
    <div
      className="rounded-xl border-l-4 cursor-pointer transition-all hover:brightness-110"
      style={{
        background: 'var(--card)',
        border: `1px solid var(--border)`,
        borderLeftColor: borderColor[d.state],
        borderLeftWidth: '3px',
      }}
      onClick={() => setOpen(o => !o)}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          {/* Left: name + category */}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                {d.instrument}
              </span>
              <span className="text-xs px-1.5 py-0.5 rounded"
                style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
                {d.category}
              </span>
            </div>
            {/* Direction */}
            {d.direction && (
              <div className={clsx('flex items-center gap-1 mt-1 text-sm font-medium', directionColor(d.direction))}>
                {d.direction === 'BULLISH'
                  ? <TrendingUp size={13} />
                  : <TrendingDown size={13} />}
                {d.direction === 'BULLISH' ? 'Bullish' : 'Bearish'}
                {d.breakout_level && (
                  <span className="text-xs font-normal ml-1" style={{ color: 'var(--text-secondary)' }}>
                    @ {d.breakout_level.toFixed(5)}
                  </span>
                )}
              </div>
            )}
            {!d.direction && (
              <div className="flex items-center gap-1 mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <Minus size={12} /> No active bias
              </div>
            )}
          </div>

          {/* Right: state badge + chevron */}
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium"
              style={{ background: badge.bg, color: badge.text }}>
              {d.state === 'RETEST_IN_PROGRESS' && (
                <span className="w-1.5 h-1.5 rounded-full pulse" style={{ background: badge.text }} />
              )}
              {d.state === 'BREAKOUT_ACTIVE' && (
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: badge.text }} />
              )}
              {stateLabel(d.state)}
            </div>
            <ChevronDown size={14} style={{ color: 'var(--text-secondary)' }}
              className={clsx('transition-transform', open && 'rotate-180')} />
          </div>
        </div>

        {/* Footer row */}
        <div className="flex items-center gap-4 mt-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
          {d.active_sources_count > 0 && (
            <span>{d.active_sources_count} active source{d.active_sources_count > 1 ? 's' : ''}</span>
          )}
          <span>Updated {timeAgo(d.last_updated)}</span>
          {d.last_alert_at && <span>Last alert {timeAgo(d.last_alert_at)}</span>}
        </div>
      </div>

      {/* Expanded detail */}
      {open && (
        <div className="px-4 pb-4 pt-0 border-t text-xs" style={{ borderColor: 'var(--border)' }}>
          <div className="mt-3 space-y-1.5" style={{ color: 'var(--text-secondary)' }}>
            <div className="flex justify-between">
              <span>State</span>
              <span style={{ color: 'var(--text-primary)' }}>{stateLabel(d.state)}</span>
            </div>
            {d.breakout_level && (
              <div className="flex justify-between">
                <span>Broken level</span>
                <span style={{ color: 'var(--text-primary)' }}>{d.breakout_level.toFixed(5)}</span>
              </div>
            )}
            {d.breakout_ts && (
              <div className="flex justify-between">
                <span>Breakout candle</span>
                <span style={{ color: 'var(--text-primary)' }}>
                  {new Date(d.breakout_ts).toLocaleDateString('en-GB', { timeZone: 'UTC' })}
                </span>
              </div>
            )}
            {d.last_alert_at && (
              <div className="flex justify-between">
                <span>Last alert</span>
                <span style={{ color: 'var(--text-primary)' }}>{timeAgo(d.last_alert_at)}</span>
              </div>
            )}
            {!d.last_alert_at && <div className="text-center py-1">No alerts fired yet</div>}
          </div>
        </div>
      )}
    </div>
  )
}
