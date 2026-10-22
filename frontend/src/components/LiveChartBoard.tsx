'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { MonitorPlay, Search } from 'lucide-react'
import { fetcher } from '@/lib/api'
import { timeAgo } from '@/lib/utils'

// Live Chart Board: what each pair's 4H Bias Pointer chart shows, refreshed by the
// script at every H4 close. Subscribers only receive the pairs they get alerts on.

interface Snapshot {
  stage: 'idle' | 'breakout' | 'retest' | 'confirmed_aligned' | 'confirmed_realigning'
  bias: 'bullish' | 'bearish' | null
  retest_source: string | null
  breakout_level: number | null
  d_a: number | null
  d_v: number | null
  d_oc: number | null
  d_oc_count: number
  h4_a: number | null
  h4_v: number | null
  h4_bk: number | null
  h4_oc: number | null
  level_type?: 'external' | 'internal' | 'inner_internal' | 'sub_internal' | null
  ext_hi?: number | null
  ext_lo?: number | null
  int_hi?: number | null
  int_lo?: number | null
  inn_hi?: number | null
  inn_lo?: number | null
  sub_hi?: number | null
  sub_lo?: number | null
}
// Weekly fields (Bias Pointer 2026-10-22+); absent on older alerts
interface WeeklySnap {
  wk_dir?: 'bullish' | 'bearish' | null
  wk_react?: boolean
  wk_src?: string | null
  wk_src_lvl?: number | null
  wk_rel?: '' | 'confirmed' | 'inline' | 'against'
  wk_cls?: 'external' | 'internal' | null
  w_hi?: number | null
  w_lo?: number | null
  w_bk?: number | null
  w_av?: number | null
  w_oc?: number | null
}
const WK = '#FFB74D'

interface BoardRow { instrument: string; snapshot: Snapshot | null; price: number | null; updated_at: string | null }

const STAGE: Record<Snapshot['stage'], string> = {
  idle: 'No breakout',
  breakout: 'Breakout · awaiting retest',
  retest: 'Retest in progress',
  confirmed_aligned: 'Confirmed · H4 aligned',
  confirmed_realigning: 'OUT OF LINE · H4 alerts paused',
}
const SOURCE: Record<string, string> = {
  post_breakout_oc: 'Post-breakout OC', daily_breaker: 'Daily Breaker', inside_range: 'Inside Range',
}
const LEVEL_TYPE: Record<string, string> = {
  external: 'External', internal: 'Internal', inner_internal: 'Inner internal', sub_internal: 'Sub-internal',
}
const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'retest', label: 'Retest' },
  { key: 'breakout', label: 'Awaiting retest' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'out', label: 'Out of line' },
  { key: 'wkconf', label: 'Weekly-confirmed' },
  { key: 'bullish', label: 'Buys' },
  { key: 'bearish', label: 'Sells' },
]

function fmt(inst: string, n: number | null): string | null {
  if (n === null || n === undefined) return null
  const d = inst.endsWith('JPY') ? 3 : n >= 1000 ? 1 : n >= 20 ? 2 : 5
  return n.toFixed(d)
}

function Level({ name, v, color }: { name: string; v: string | null; color?: string }) {
  if (!v) return null
  return <span style={{ whiteSpace: 'nowrap' }}><span style={{ color: color ?? 'var(--text-muted)' }}>{name}</span> {v}</span>
}

// One line on the Weekly: direction, what it is doing, and how the Daily relates
function weeklyLine(w: WeeklySnap, inst: string): string | null {
  if (!w.wk_dir) return null
  const dir = w.wk_dir === 'bullish' ? 'Weekly Buy' : 'Weekly Sell'
  if (w.wk_rel === 'confirmed') return `${dir} · Daily ${w.wk_cls === 'internal' ? 'Internal' : 'External'} break Weekly-confirmed`
  if (w.wk_rel === 'against') return `${dir} · Daily is AGAINST the Weekly`
  if (w.wk_react) return `${dir} · reacting at ${w.wk_src ?? 'a Weekly level'}${w.wk_src_lvl != null ? ' @ ' + fmt(inst, w.wk_src_lvl) : ''}`
  return `${dir} · waiting for a Weekly reaction`
}

export default function LiveChartBoard() {
  const { data } = useSWR<{ pairs: BoardRow[] }>('/api/chart-board', fetcher, { refreshInterval: 60000 })
  const [filter, setFilter] = useState('all')
  const [q, setQ] = useState('')

  const rows = (data?.pairs ?? [])
    .filter(r => !q || r.instrument.includes(q.toUpperCase().replace('/', '')))
    .filter(r => {
      const s = r.snapshot
      if (filter === 'all') return true
      if (!s) return false
      if (filter === 'confirmed') return s.stage === 'confirmed_aligned'
      if (filter === 'out') return s.stage === 'confirmed_realigning'
      if (filter === 'wkconf') return (s as Snapshot & WeeklySnap).wk_rel === 'confirmed'
      if (filter === 'bullish' || filter === 'bearish') return s.bias === filter
      return s.stage === filter
    })
    .sort((a, b) => {
      const order = { retest: 0, breakout: 1, confirmed_aligned: 2, confirmed_realigning: 3, idle: 4 }
      const oa = a.snapshot ? order[a.snapshot.stage] : 5
      const ob = b.snapshot ? order[b.snapshot.stage] : 5
      return oa - ob || a.instrument.localeCompare(b.instrument)
    })
  const reporting = (data?.pairs ?? []).filter(r => r.snapshot).length

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MonitorPlay size={15} color="var(--accent-hover)" />
          <h3 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Live Chart Board</h3>
          {data && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{reporting}/{data.pairs.length} pairs reporting</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)' }}>
          <Search size={12} color="var(--text-muted)" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search pair"
            style={{ width: 110, background: 'none', border: 'none', outline: 'none', color: 'var(--text-primary)', fontSize: 12 }} />
        </div>
      </div>

      <div style={{ padding: '10px 20px', display: 'flex', gap: 6, flexWrap: 'wrap', borderBottom: '1px solid var(--border)' }}>
        {FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, cursor: 'pointer',
              border: '1px solid ' + (filter === f.key ? 'var(--accent)' : 'var(--border)'),
              background: filter === f.key ? 'var(--accent-bg)' : 'transparent',
              color: filter === f.key ? 'var(--accent-hover)' : 'var(--text-secondary)' }}>
            {f.label}
          </button>
        ))}
      </div>

      {!data ? (
        <p style={{ padding: '24px 20px', fontSize: 13, color: 'var(--text-secondary)' }}>Loading…</p>
      ) : rows.length === 0 ? (
        <div style={{ padding: '28px 20px', textAlign: 'center', fontSize: 13, color: 'var(--text-secondary)' }}>
          {reporting === 0 ? 'Charts report at each H4 close — the board fills in after the next one.' : 'No pairs match this filter.'}
        </div>
      ) : (
        <div style={{ maxHeight: 520, overflowY: 'auto' }}>
          {rows.map(r => {
            const s = r.snapshot
            const dirCol = s?.bias === 'bullish' ? 'var(--bullish)' : s?.bias === 'bearish' ? 'var(--bearish)' : 'var(--text-muted)'
            const i = r.instrument
            return (
              <div key={i} style={{ padding: '11px 20px', borderBottom: '1px solid var(--border)', display: 'flex', flexWrap: 'wrap', gap: '6px 16px', alignItems: 'center' }}>
                <div style={{ minWidth: 150, flex: '0 0 auto' }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{i}</div>
                  {s ? (
                    <div style={{ fontSize: 11, fontWeight: 600, color: dirCol, marginTop: 2 }}>
                      {s.bias ? (s.bias === 'bullish' ? 'Buy · ' : 'Sell · ') : ''}{STAGE[s.stage]}
                      {s.stage === 'retest' && s.retest_source ? ` (${SOURCE[s.retest_source] ?? s.retest_source})` : ''}
                      {s.level_type && s.stage !== 'idle' ? ` · ${LEVEL_TYPE[s.level_type] ?? s.level_type} break` : ''}
                    </div>
                  ) : (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Waiting for the next H4 close</div>
                  )}
                </div>
                {s && (() => {
                  const w = s as Snapshot & WeeklySnap
                  const line = weeklyLine(w, i)
                  if (!line) return null
                  const against = w.wk_rel === 'against'
                  return (
                    <div style={{ minWidth: 170, flex: '0 1 230px', fontSize: 11, fontWeight: 600, lineHeight: 1.45,
                      color: against ? 'var(--warning)' : WK, borderLeft: `2px solid ${against ? 'var(--warning)' : WK}`, paddingLeft: 8 }}>
                      {line}
                    </div>
                  )
                })()}
                {s && (
                  <div style={{ flex: '1 1 260px', display: 'flex', flexWrap: 'wrap', gap: '3px 12px', fontSize: 11.5, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {(() => {
                      const w = s as Snapshot & WeeklySnap
                      return <>
                        <Level name="W.H" color={WK} v={fmt(i, w.w_hi ?? null)} />
                        <Level name="W.L" color={WK} v={fmt(i, w.w_lo ?? null)} />
                        <Level name="W.BK" color={WK} v={fmt(i, w.w_bk ?? null)} />
                        <Level name={w.wk_dir === 'bearish' ? 'W.A' : 'W.V'} color={WK} v={fmt(i, w.w_av ?? null)} />
                        <Level name="W.OC" color={WK} v={fmt(i, w.w_oc ?? null)} />
                      </>
                    })()}
                    <Level name="Ext.H" v={fmt(i, s.ext_hi ?? null)} />
                    <Level name="Ext.L" v={fmt(i, s.ext_lo ?? null)} />
                    <Level name="Int.H" v={fmt(i, s.int_hi ?? null)} />
                    <Level name="Int.L" v={fmt(i, s.int_lo ?? null)} />
                    <Level name="Inn.H" v={fmt(i, s.inn_hi ?? null)} />
                    <Level name="Inn.L" v={fmt(i, s.inn_lo ?? null)} />
                    <Level name="Sub.H" v={fmt(i, s.sub_hi ?? null)} />
                    <Level name="Sub.L" v={fmt(i, s.sub_lo ?? null)} />
                    <Level name="D.A" v={fmt(i, s.d_a)} />
                    <Level name="D.V" v={fmt(i, s.d_v)} />
                    {s.d_oc !== null && <Level name="D.OC" v={fmt(i, s.d_oc) + (s.d_oc_count > 1 ? ` (${s.d_oc_count} watched)` : '')} />}
                    <Level name="H4.A" v={fmt(i, s.h4_a)} />
                    <Level name="H4.V" v={fmt(i, s.h4_v)} />
                    <Level name="H4.BK" v={fmt(i, s.h4_bk)} />
                    <Level name="H4.OC" v={fmt(i, s.h4_oc)} />
                  </div>
                )}
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto', textAlign: 'right' }}>
                  {r.price !== null && <div style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{fmt(i, r.price)}</div>}
                  {r.updated_at && <div>{timeAgo(r.updated_at)}</div>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
