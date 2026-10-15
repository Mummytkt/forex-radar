'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher } from '@/lib/api'
import { timeAgo, sourceTypeLabel } from '@/lib/utils'
import { useTimezone } from '@/lib/timezone'
import type { AlertsPage, AlertItem } from '@/lib/types'

function AlertRow({ a, isLast }: { a: AlertItem; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const { fmtDate } = useTimezone()
  const bull = a.direction === 'BULLISH'

  const copy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(a.alert_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      <tr onClick={() => setExpanded(e => !e)} style={{ borderBottom: isLast && !expanded ? 'none' : undefined }}>
        <td>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, flexShrink: 0,
              background: bull ? 'var(--bullish-bg)' : 'var(--bearish-bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              {bull ? <TrendingUp size={14} color="var(--bullish)" /> : <TrendingDown size={14} color="var(--bearish)" />}
            </div>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{a.instrument}</span>
          </div>
        </td>
        <td>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>D1 → H4</span>
        </td>
        <td>
          <div style={{ fontSize: 13 }}>
            <span style={{ color: bull ? 'var(--bullish)' : 'var(--bearish)', fontWeight: 600 }}>
              {bull ? 'Buy' : 'Sell'}
            </span>
            <span style={{ color: 'var(--text-secondary)', marginLeft: 6 }}>
              · {a.h4_classification} bias
            </span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sourceTypeLabel(a.source_type)}</div>
        </td>
        <td>
          <div style={{ fontSize: 13 }}>{fmtDate(a.fired_at)}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{timeAgo(a.fired_at)}</div>
        </td>
        <td>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="badge badge-delivered" style={{ fontSize: 11 }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
              Delivered
            </span>
            <button onClick={copy} style={{
              width: 26, height: 26, borderRadius: 6, border: 'none', cursor: 'pointer',
              background: 'var(--border)', color: 'var(--text-secondary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.1s',
            }} title="Copy">
              {copied ? <Check size={12} color="var(--bullish)" /> : <Copy size={12} />}
            </button>
            {expanded ? <ChevronUp size={13} color="var(--text-muted)" /> : <ChevronDown size={13} color="var(--text-muted)" />}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5} style={{ padding: '0 16px 16px', borderBottom: isLast ? 'none' : '1px solid var(--border)' }}>
            <pre style={{
              fontSize: 12, whiteSpace: 'pre-wrap', fontFamily: 'monospace',
              padding: '12px 16px', borderRadius: 8, lineHeight: 1.7,
              background: 'var(--bg)', color: 'var(--text-primary)',
              border: '1px solid var(--border)', maxHeight: 300, overflow: 'auto',
            }}>
              {a.alert_text}
            </pre>
          </td>
        </tr>
      )}
    </>
  )
}

export default function HistoryPage() {
  const [page, setPage] = useState(0)
  const [dirFilter, setDirFilter] = useState('')
  const [pairFilter, setPairFilter] = useState('')
  const limit = 20

  const { data } = useSWR<AlertsPage>(
    `/api/alerts?limit=${limit}&offset=${page * limit}`
      + (dirFilter ? `&direction=${dirFilter}` : '')
      + (pairFilter ? `&instrument=${encodeURIComponent(pairFilter)}` : ''),
    fetcher, { refreshInterval: 60000 }
  )
  const { data: pairList } = useSWR<{ instruments: string[] }>('/api/alerts/instruments', fetcher, { refreshInterval: 300000 })

  const totalPages = data ? Math.ceil(data.total / limit) : 0
  const filtering = !!(dirFilter || pairFilter)
  const clearFilters = () => { setDirFilter(''); setPairFilter(''); setPage(0) }

  return (
    <>
      <TopBar title="Alert History" subtitle="Every notification delivered to your Telegram" />
      <main className="page-padded" style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: 18 }}>

        {/* Filter bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {data ? `${data.total} alert${data.total !== 1 ? 's' : ''}${filtering ? ' match' : ' total'}` : 'Loading…'}
          </span>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <select
              id="history-pair-filter"
              aria-label="Filter by pair"
              value={pairFilter}
              onChange={e => { setPairFilter(e.target.value); setPage(0) }}
              style={{
                padding: '6px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                border: '1px solid', outline: 'none',
                borderColor: pairFilter ? 'var(--accent)' : 'var(--border)',
                background: 'var(--card)', color: pairFilter ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}>
              <option value="">All pairs</option>
              {(pairList?.instruments ?? []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            {[['', 'All'], ['BULLISH', '↑ Buy'], ['BEARISH', '↓ Sell']].map(([val, label]) => (
              <button key={val} onClick={() => { setDirFilter(val); setPage(0) }}
                style={{
                  padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                  border: '1px solid', cursor: 'pointer',
                  borderColor: dirFilter === val ? 'var(--accent)' : 'var(--border)',
                  background: dirFilter === val ? 'var(--accent)' : 'var(--card)',
                  color: dirFilter === val ? 'white' : 'var(--text-secondary)',
                  transition: 'all 0.12s',
                }}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          {!data && (
            <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</div>
          )}
          {data?.items.length === 0 && (filtering ? (
            <div style={{ padding: '48px', textAlign: 'center', fontSize: 13, color: 'var(--text-secondary)' }}>
              <p style={{ fontWeight: 600 }}>No alerts match this filter.</p>
              <button onClick={clearFilters}
                style={{ marginTop: 10, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: 'var(--card-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border)', cursor: 'pointer' }}>
                Clear filters
              </button>
            </div>
          ) : (
            <div style={{ padding: '48px', textAlign: 'center', fontSize: 13, color: 'var(--text-secondary)' }}>
              <p style={{ fontWeight: 600 }}>No alerts fired yet.</p>
              <p style={{ fontSize: 12, marginTop: 6, color: 'var(--text-muted)' }}>
                Alerts fire when a Daily breakout, reaction source retest, and H4 confirmation all align.
              </p>
            </div>
          ))}
          {data && data.items.length > 0 && (
            <div className="table-wrap"><table className="data-table">
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Timeframe</th>
                  <th>Notification</th>
                  <th>Delivered</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((a, i) => (
                  <AlertRow key={a.id} a={a} isLast={i === data.items.length - 1} />
                ))}
              </tbody>
            </table></div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
              style={{
                padding: '7px 16px', borderRadius: 8, fontSize: 12,
                border: '1px solid var(--border)', background: 'var(--card)',
                color: 'var(--text-secondary)', cursor: 'pointer', opacity: page === 0 ? 0.4 : 1,
              }}>Previous</button>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{page + 1} / {totalPages}</span>
            <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}
              style={{
                padding: '7px 16px', borderRadius: 8, fontSize: 12,
                border: '1px solid var(--border)', background: 'var(--card)',
                color: 'var(--text-secondary)', cursor: 'pointer', opacity: page >= totalPages - 1 ? 0.4 : 1,
              }}>Next</button>
          </div>
        )}
      </main>
    </>
  )
}
