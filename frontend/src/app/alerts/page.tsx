'use client'
import { useState } from 'react'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher } from '@/lib/api'
import type { AlertsPage, AlertItem, Direction } from '@/lib/types'
import { fmtDate, timeAgo, sourceTypeLabel } from '@/lib/utils'

function AlertCard({ a }: { a: AlertItem }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const bull = a.direction === 'BULLISH'

  const copy = async () => {
    await navigator.clipboard.writeText(a.alert_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <div className="p-4 flex items-start gap-4 cursor-pointer" onClick={() => setExpanded(e => !e)}>
        {/* Direction icon */}
        <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ background: bull ? '#10B98122' : '#EF444422' }}>
          {bull
            ? <TrendingUp size={16} style={{ color: '#10B981' }} />
            : <TrendingDown size={16} style={{ color: '#EF4444' }} />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{a.instrument}</span>
            <span className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: bull ? '#10B98122' : '#EF444422', color: bull ? '#10B981' : '#EF4444' }}>
              {a.direction}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
              {sourceTypeLabel(a.source_type)}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
              {a.h4_classification}
            </span>
          </div>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
            {fmtDate(a.fired_at)} · {timeAgo(a.fired_at)}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button onClick={e => { e.stopPropagation(); copy() }}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}
            title="Copy alert text">
            {copied ? <Check size={13} style={{ color: '#10B981' }} /> : <Copy size={13} />}
          </button>
          {expanded ? <ChevronUp size={14} style={{ color: 'var(--text-secondary)' }} />
            : <ChevronDown size={14} style={{ color: 'var(--text-secondary)' }} />}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <pre className="mt-3 text-xs whitespace-pre-wrap leading-relaxed font-mono p-3 rounded-lg overflow-auto"
            style={{ background: 'var(--surface)', color: 'var(--text-primary)', maxHeight: '320px' }}>
            {a.alert_text}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function AlertsPage() {
  const [page, setPage] = useState(0)
  const [dirFilter, setDirFilter] = useState<string>('')
  const limit = 20

  const { data } = useSWR<AlertsPage>(
    `/api/alerts?limit=${limit}&offset=${page * limit}${dirFilter ? `&direction=${dirFilter}` : ''}`,
    fetcher, { refreshInterval: 60000 }
  )

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  return (
    <>
      <TopBar title="Alerts" />
      <main className="flex-1 p-6 space-y-4">
        {/* Filter bar */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {data ? `${data.total} alert${data.total !== 1 ? 's' : ''} total` : 'Loading…'}
          </span>
          <div className="flex gap-2 ml-auto">
            {(['', 'BULLISH', 'BEARISH'] as const).map(d => (
              <button key={d}
                onClick={() => { setDirFilter(d); setPage(0) }}
                className="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                style={dirFilter === d
                  ? { background: 'var(--accent)', color: 'white' }
                  : { background: 'var(--card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }
                }>
                {d === '' ? 'All' : d === 'BULLISH' ? '↑ Bullish' : '↓ Bearish'}
              </button>
            ))}
          </div>
        </div>

        {/* Alert cards */}
        {!data && <div className="text-center py-16 text-sm" style={{ color: 'var(--text-secondary)' }}>Loading…</div>}
        {data?.items.length === 0 && (
          <div className="text-center py-16 rounded-xl" style={{ background: 'var(--card)', color: 'var(--text-secondary)' }}>
            <p className="text-sm">No alerts fired yet.</p>
            <p className="text-xs mt-1">The engine will send alerts here when all 4 conditions are met.</p>
          </div>
        )}
        <div className="space-y-3">
          {data?.items.map(a => <AlertCard key={a.id} a={a} />)}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
              className="px-3 py-1.5 text-xs rounded-lg disabled:opacity-40"
              style={{ background: 'var(--card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              Previous
            </button>
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {page + 1} / {totalPages}
            </span>
            <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}
              className="px-3 py-1.5 text-xs rounded-lg disabled:opacity-40"
              style={{ background: 'var(--card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              Next
            </button>
          </div>
        )}
      </main>
    </>
  )
}
