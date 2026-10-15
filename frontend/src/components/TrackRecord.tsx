'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { API_BASE } from '@/lib/api'

interface Outcome {
  instrument: string; direction: string; fired_at: string; unit: 'pips' | '%'
  move_24h: number; move_5d: number; move_24h_pct: number; move_5d_pct: number
}
interface TrackRecordData {
  tracking_since: string | null; evaluated: number; running: number; min_sample: number
  in_profit_24h_pct: number | null; in_profit_5d_pct: number | null; recent: Outcome[]
}

const fmtDate = (s: string) =>
  new Date(s.slice(0, 19) + 'Z').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })

function Move({ o, h }: { o: Outcome; h: '24h' | '5d' }) {
  const v = o.unit === 'pips' ? (h === '24h' ? o.move_24h : o.move_5d) : (h === '24h' ? o.move_24h_pct : o.move_5d_pct)
  const txt = o.unit === 'pips' ? `${v > 0 ? '+' : ''}${v.toFixed(1)} pips` : `${v > 0 ? '+' : ''}${v.toFixed(2)}%`
  return <span style={{ fontWeight: 700, color: v > 0 ? 'var(--bullish)' : v < 0 ? 'var(--bearish)' : 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>{txt}</span>
}

function Stat({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '20px 18px', textAlign: 'center' }}>
      <div style={{ fontSize: 34, fontWeight: 800, color, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4 }}>{label}</div>
    </div>
  )
}

/** Landing-page section: outcomes of Origin bias calls, published once each is 5 days old. */
export default function TrackRecord() {
  const [data, setData] = useState<TrackRecordData | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/public/track-record`)
      .then(r => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {})
  }, [])

  if (!data) return null
  const enough = data.in_profit_5d_pct !== null

  return (
    <section id="track-record" style={{ maxWidth: 940, margin: '0 auto', padding: '20px 24px 80px' }}>
      <div style={{ textAlign: 'center', marginBottom: 30 }}>
        <h2 style={{ fontSize: 'clamp(26px, 4vw, 34px)', fontWeight: 800, marginBottom: 10, letterSpacing: '-0.02em' }}>Every call, measured in public.</h2>
        <p style={{ fontSize: 15, color: 'var(--text-secondary)', maxWidth: 620, margin: '0 auto', lineHeight: 1.65 }}>
          We check every Origin bias call against the market: where price was 24 hours and 5 days later, in the direction we called.
          Nothing is hand-picked.
        </p>
      </div>

      {enough ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14, marginBottom: 20 }}>
          <Stat value={`${data.in_profit_24h_pct}%`} label="in profit after 24 hours" color="var(--accent)" />
          <Stat value={`${data.in_profit_5d_pct}%`} label="in profit after 5 days" color="var(--bullish)" />
          <Stat value={`${data.evaluated}`} label="calls measured" color="var(--text-primary)" />
        </div>
      ) : (
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '20px 22px', marginBottom: 20, textAlign: 'center' }}>
          <p style={{ fontWeight: 700, fontSize: 15 }}>Building the record: {data.evaluated} of {data.min_sample} calls measured</p>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.6 }}>
            Results go public once {data.min_sample} calls have finished their 5-day window, so a handful of trades can&apos;t paint a misleading picture.
            {data.tracking_since ? ` Tracking since ${fmtDate(data.tracking_since)}.` : ''}
            {data.running > 0 ? ` ${data.running} recent call${data.running === 1 ? ' is' : 's are'} still inside the window.` : ''}
          </p>
        </div>
      )}

      {data.recent.length > 0 && (
        <div className="table-wrap" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
          <table className="data-table" style={{ minWidth: 520 }}>
            <thead>
              <tr><th>Pair</th><th>Call</th><th>Date</th><th>After 24h</th><th>After 5 days</th></tr>
            </thead>
            <tbody>
              {data.recent.map(o => {
                const bull = o.direction === 'bullish'
                return (
                  <tr key={o.instrument + o.fired_at}>
                    <td style={{ fontWeight: 700 }}>{o.instrument}</td>
                    <td>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontWeight: 600, color: bull ? 'var(--bullish)' : 'var(--bearish)' }}>
                        {bull ? <TrendingUp size={13} /> : <TrendingDown size={13} />}{bull ? 'Buy' : 'Sell'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{fmtDate(o.fired_at)}</td>
                    <td><Move o={o} h="24h" /></td>
                    <td><Move o={o} h="5d" /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', marginTop: 14, lineHeight: 1.7, maxWidth: 680, marginLeft: 'auto', marginRight: 'auto' }}>
        Measured on TradingView H4 closing prices, from the close nearest each alert. Calls appear here 5 days after they fire, so live signals stay
        with members. Currency pairs and gold are shown in pips; indices, oil and crypto in %. Past results don&apos;t guarantee future results —
        see the <Link href="/risk" style={{ color: 'var(--accent)', textDecoration: 'none' }}>Risk Disclaimer</Link>.
      </p>
    </section>
  )
}
