'use client'
import { useEffect, useState, useCallback } from 'react'
import { DollarSign, Users, RefreshCw, Gift, Activity, Database, LineChart, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useTimezone } from '@/lib/timezone'
import { timeAgo } from '@/lib/utils'

function api(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}), 'Content-Type': 'application/json' },
  })
}

const PLAN_LABEL: Record<string, string> = {
  TESTER: 'Tester', TRIAL: 'Free trial', '30DAY': '30 days', '6MONTH': '6 months', '9MONTH': '9 months', '12MONTH': '12 months', LIFETIME: 'Lifetime',
}
const usd = (n: number) => `$${n.toLocaleString(undefined, { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 })}`

interface Business {
  subscribers: {
    active: number; by_plan: Record<string, number>; auto_renew_on: number; telegram_linked: number
    new_30d: number; expired_30d: number; cancelled_auto_renew_30d: number
    expiring_7d: { name: string; email: string; plan: string; plan_expires_at: string; auto_renew: boolean }[]
  }
  revenue: { this_month_usd: number; last_30d_usd: number; all_time_usd: number; payments_all_time: number; monthly: { month: string; revenue_usd: number }[] }
  affiliates: { id: number; name: string; email: string; code: string; paid_customers: number; pending_usd: number; available_usd: number; paid_usd: number }[]
  commissions_owed_usd: number
}
interface Feed { instrument: string; last_seen_at: string; last_type: string; status: 'ok' | 'silent' | 'closed' }
interface Track { evaluated: number; running: number; min_sample: number; in_profit_24h_pct: number | null; in_profit_5d_pct: number | null; tracking_since: string | null }

const card: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }
const head: React.CSSProperties = { padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', gap: 8 }
const h2: React.CSSProperties = { fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }

function Tile({ icon: Icon, label, value, note }: { icon: React.ElementType; label: string; value: string; note?: string }) {
  return (
    <div style={{ ...card, padding: '16px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>
        <Icon size={13} color="var(--accent-hover)" /> {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, marginTop: 6, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {note && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{note}</div>}
    </div>
  )
}

/** Monthly revenue: one series, so one hue and no legend; hover/focus shows the exact figure. */
function RevenueBars({ data }: { data: { month: string; revenue_usd: number }[] }) {
  const [hover, setHover] = useState<number | null>(null)
  const max = Math.max(...data.map(d => d.revenue_usd), 1)
  const label = (m: string) => new Date(m + '-01T00:00:00Z').toLocaleDateString(undefined, { month: 'short', timeZone: 'UTC' })
  const last = data.length - 1
  return (
    <div>
      <div role="img" aria-label="Revenue per month for the last six months" style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 150, padding: '18px 4px 0', borderBottom: '1px solid var(--border)' }}>
        {data.map((d, i) => {
          const h = d.revenue_usd > 0 ? Math.max(4, (d.revenue_usd / max) * 128) : 0
          const show = hover === i || (hover === null && i === last)
          return (
            <div key={d.month} tabIndex={0} aria-label={`${label(d.month)}: ${usd(d.revenue_usd)}`}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)} onBlur={() => setHover(null)}
              style={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', position: 'relative', cursor: 'default', outline: 'none' }}>
              {show && (
                <div style={{ position: 'absolute', bottom: h + 6, fontSize: 11.5, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                  {usd(d.revenue_usd)}
                </div>
              )}
              <div style={{ width: '62%', maxWidth: 38, height: h, background: 'var(--accent)', opacity: hover === null || hover === i ? 1 : 0.55, borderRadius: '4px 4px 0 0', transition: 'opacity 0.12s' }} />
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', gap: 2, padding: '6px 4px 0' }}>
        {data.map(d => <div key={d.month} style={{ flex: 1, textAlign: 'center', fontSize: 11, color: 'var(--text-muted)' }}>{label(d.month)}</div>)}
      </div>
      <table style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>
        <caption>Revenue per month</caption>
        <tbody>{data.map(d => <tr key={d.month}><th>{label(d.month)}</th><td>{usd(d.revenue_usd)}</td></tr>)}</tbody>
      </table>
    </div>
  )
}

export default function BusinessPage() {
  const { user } = useAuth()
  const { fmtDate } = useTimezone()
  const [biz, setBiz] = useState<Business | null>(null)
  const [feed, setFeed] = useState<Feed[] | null>(null)
  const [track, setTrack] = useState<Track | null>(null)
  const [error, setError] = useState('')
  const [confirmPay, setConfirmPay] = useState<number | null>(null)
  const [backup, setBackup] = useState<{ busy: boolean; result?: string; ok?: boolean }>({ busy: false })

  const load = useCallback(() => {
    api('/api/admin/business').then(r => (r.ok ? r.json() : Promise.reject(r.status))).then(setBiz)
      .catch(() => setError("Couldn't load business figures. Refresh to try again."))
    api('/api/admin/feed-health').then(r => (r.ok ? r.json() : null)).then(d => d && setFeed(d.instruments)).catch(() => {})
    fetch(`${API_BASE}/api/public/track-record`).then(r => (r.ok ? r.json() : null)).then(setTrack).catch(() => {})
  }, [])

  useEffect(() => { if (user?.role === 'OWNER') load() }, [user, load])

  const markPaid = async (id: number) => {
    if (confirmPay !== id) { setConfirmPay(id); setTimeout(() => setConfirmPay(c => (c === id ? null : c)), 4000); return }
    setConfirmPay(null)
    const r = await api('/api/admin/commissions/mark-paid', { method: 'POST', body: JSON.stringify({ affiliate_id: id }) })
    if (r.ok) load()
  }

  const runBackup = async () => {
    setBackup({ busy: true })
    try {
      const r = await api('/api/admin/backup', { method: 'POST' })
      const d = await r.json()
      if (!r.ok || d.error) throw new Error(d.error || d.detail || 'Backup failed')
      setBackup({ busy: false, ok: d.integrity_ok, result:
        `${d.file} · ${d.size_kb} KB · integrity ${d.integrity_ok ? 'OK' : 'FAILED'} · `
        + (d.offsite_sent
          ? `encrypted copy sent to ${d.destination === 'channel' ? 'your backups channel' : 'your Telegram chat'}`
            + (d.old_deleted ? ` · ${d.old_deleted} old backup${d.old_deleted === 1 ? '' : 's'} removed` : '')
          : 'off-site copy not sent') })
    } catch (e: unknown) {
      setBackup({ busy: false, ok: false, result: e instanceof Error ? e.message : 'Backup failed' })
    }
  }

  if (user && user.role !== 'OWNER') {
    return (<><TopBar title="Business" subtitle="Owner only" /><main className="page-padded" style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 14 }}>This page is only available to the platform owner.</main></>)
  }

  const silent = feed?.filter(f => f.status === 'silent') ?? []
  const s = biz?.subscribers
  const rev = biz?.revenue

  return (
    <>
      <TopBar title="Business" subtitle="Revenue, subscribers, payouts and platform health" />
      <main className="page-padded" style={{ flex: 1, width: '100%', padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
        {error && <div style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>{error}</div>}

        {/* Headline numbers */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <Tile icon={DollarSign} label="Revenue this month" value={rev ? usd(rev.this_month_usd) : '—'} note={rev ? `${usd(rev.last_30d_usd)} in the last 30 days` : undefined} />
          <Tile icon={Users} label="Active subscribers" value={s ? String(s.active) : '—'} note={s ? `${s.new_30d} new in 30 days` : undefined} />
          <Tile icon={RefreshCw} label="On auto-renew" value={s ? String(s.auto_renew_on) : '—'} note={s ? `${s.cancelled_auto_renew_30d} turned it off in 30 days` : undefined} />
          <Tile icon={Gift} label="Commissions owed" value={biz ? usd(biz.commissions_owed_usd) : '—'} note="Ready to pay affiliates" />
        </div>

        <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 16, alignItems: 'start' }}>
          {/* Revenue chart */}
          <div style={card}>
            <div style={head}><LineChart size={14} color="var(--accent-hover)" /><h2 style={h2}>Revenue per month</h2></div>
            <div style={{ padding: '8px 18px 18px', position: 'relative' }}>
              {rev ? <RevenueBars data={rev.monthly} /> : <p style={{ fontSize: 13, color: 'var(--text-secondary)', padding: '20px 0' }}>Loading…</p>}
              {rev && <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 10 }}>
                All time: {usd(rev.all_time_usd)} from {rev.payments_all_time} payment{rev.payments_all_time === 1 ? '' : 's'}. USD as charged; free-trial card checks excluded.
              </p>}
            </div>
          </div>

          {/* Subscribers */}
          <div style={card}>
            <div style={head}><Users size={14} color="var(--accent-hover)" /><h2 style={h2}>Subscribers</h2></div>
            <div style={{ padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13 }}>
              {s ? <>
                {Object.entries(s.by_plan).sort((a, b) => b[1] - a[1]).map(([plan, n]) => (
                  <div key={plan} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{PLAN_LABEL[plan] ?? plan}</span>
                    <strong style={{ fontVariantNumeric: 'tabular-nums' }}>{n}</strong>
                  </div>
                ))}
                {Object.keys(s.by_plan).length === 0 && <span style={{ color: 'var(--text-muted)' }}>No active subscribers yet.</span>}
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 9, display: 'flex', flexDirection: 'column', gap: 7, color: 'var(--text-secondary)' }}>
                  <span>Telegram linked: <strong style={{ color: 'var(--text-primary)' }}>{s.telegram_linked} of {s.active}</strong></span>
                  <span>Access ended (30 days): <strong style={{ color: 'var(--text-primary)' }}>{s.expired_30d}</strong></span>
                </div>
              </> : <span style={{ color: 'var(--text-secondary)' }}>Loading…</span>}
            </div>
          </div>
        </div>

        {/* Expiring soon */}
        {s && s.expiring_7d.length > 0 && (
          <div style={card}>
            <div style={head}><AlertTriangle size={14} color="var(--warning)" /><h2 style={h2}>Ending in the next 7 days</h2></div>
            <div className="table-wrap"><table className="data-table" style={{ minWidth: 480 }}>
              <thead><tr><th>Subscriber</th><th>Plan</th><th>Ends</th><th>Auto-renew</th></tr></thead>
              <tbody>{s.expiring_7d.map(u => (
                <tr key={u.email}>
                  <td><div style={{ fontWeight: 600 }}>{u.name || '—'}</div><div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{u.email}</div></td>
                  <td>{PLAN_LABEL[u.plan] ?? u.plan}</td>
                  <td>{fmtDate(u.plan_expires_at)}</td>
                  <td style={{ color: u.auto_renew ? 'var(--bullish)' : 'var(--text-secondary)', fontWeight: 600 }}>{u.auto_renew ? 'On — will charge' : 'Off'}</td>
                </tr>))}
              </tbody>
            </table></div>
          </div>
        )}

        {/* Affiliates */}
        <div style={card}>
          <div style={head}><Gift size={14} color="var(--accent-hover)" /><h2 style={h2}>Affiliate payouts</h2></div>
          {biz && biz.affiliates.length > 0 ? (
            <div className="table-wrap"><table className="data-table" style={{ minWidth: 640 }}>
              <thead><tr><th>Affiliate</th><th>Code</th><th>Paying customers</th><th>On hold</th><th>Owed now</th><th>Paid</th><th></th></tr></thead>
              <tbody>{biz.affiliates.map(a => (
                <tr key={a.id}>
                  <td><div style={{ fontWeight: 600 }}>{a.name || '—'}</div><div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{a.email}</div></td>
                  <td style={{ fontFamily: 'monospace' }}>{a.code}</td>
                  <td>{a.paid_customers}</td>
                  <td>{usd(a.pending_usd)}</td>
                  <td style={{ fontWeight: 700, color: a.available_usd > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>{usd(a.available_usd)}</td>
                  <td>{usd(a.paid_usd)}</td>
                  <td>{a.available_usd > 0 && (
                    <button onClick={() => markPaid(a.id)} style={{ padding: '5px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap', border: 'none',
                      background: confirmPay === a.id ? 'var(--bullish)' : 'var(--bullish-bg)', color: confirmPay === a.id ? 'white' : 'var(--bullish)' }}>
                      {confirmPay === a.id ? `Confirm ${usd(a.available_usd)} paid` : 'Mark as paid'}
                    </button>)}
                  </td>
                </tr>))}
              </tbody>
            </table></div>
          ) : (
            <p style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-secondary)' }}>{biz ? 'No affiliates yet.' : 'Loading…'}</p>
          )}
          <p style={{ padding: '0 20px 14px', fontSize: 11.5, color: 'var(--text-muted)' }}>
            Commission is held 7 days after each customer payment, then becomes owed. Pay the affiliate yourself, then mark it paid here.
          </p>
        </div>

        <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>
          {/* Signal feed health */}
          <div style={card}>
            <div style={head}><Activity size={14} color="var(--accent-hover)" /><h2 style={h2}>TradingView signal feed</h2></div>
            <div style={{ padding: '14px 20px', fontSize: 13 }}>
              {!feed ? <span style={{ color: 'var(--text-secondary)' }}>Loading…</span>
                : feed.length === 0 ? <span style={{ color: 'var(--text-secondary)' }}>No pairs have reported yet. They appear after the next H4 close.</span>
                : <>
                  <p style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, color: silent.length ? 'var(--bearish)' : 'var(--bullish)' }}>
                    {silent.length ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                    {silent.length ? `${silent.length} pair${silent.length === 1 ? '' : 's'} silent — check TradingView alerts` : `All ${feed.length} pairs reporting normally`}
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
                    {feed.map(f => (
                      <span key={f.instrument} title={`Last heard ${timeAgo(f.last_seen_at)} (${f.last_type})`}
                        style={{ fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 999, border: '1px solid var(--border)',
                          color: f.status === 'silent' ? 'var(--bearish)' : f.status === 'closed' ? 'var(--text-muted)' : 'var(--text-secondary)',
                          background: f.status === 'silent' ? 'var(--bearish-bg)' : 'transparent' }}>
                        {f.status === 'silent' ? '⚠ ' : ''}{f.instrument}
                      </span>
                    ))}
                  </div>
                  <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 10 }}>Greyed pairs are in a closed market. You also get a Telegram warning if a pair goes quiet for 5 hours.</p>
                </>}
            </div>
          </div>

          {/* Track record + backups */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={card}>
              <div style={head}><LineChart size={14} color="var(--accent-hover)" /><h2 style={h2}>Public track record</h2></div>
              <div style={{ padding: '14px 20px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {!track ? 'Loading…' : track.in_profit_5d_pct !== null
                  ? <>In profit after 24h: <strong style={{ color: 'var(--text-primary)' }}>{track.in_profit_24h_pct}%</strong> · after 5 days: <strong style={{ color: 'var(--text-primary)' }}>{track.in_profit_5d_pct}%</strong> · {track.evaluated} calls measured</>
                  : <>{track.evaluated} of {track.min_sample} calls measured — the public stats appear at {track.min_sample}. {track.running} recent call{track.running === 1 ? ' is' : 's are'} inside the 5-day window.</>}
                <div><a href="/#track-record" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600, fontSize: 12 }}>See it on the landing page</a></div>
              </div>
            </div>
            <div style={card}>
              <div style={head}><Database size={14} color="var(--accent-hover)" /><h2 style={h2}>Backups</h2></div>
              <div style={{ padding: '14px 20px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                <p>Automatic every day at 02:30 UTC: a copy on the server (last 7 kept) and an encrypted copy sent to Telegram.
                  With a private backups channel connected, copies older than 30 days are deleted there automatically.</p>
                <button onClick={runBackup} disabled={backup.busy}
                  style={{ marginTop: 10, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer', background: 'var(--accent)', color: 'white', opacity: backup.busy ? 0.6 : 1 }}>
                  {backup.busy ? <><Loader2 size={12} className="spin" /> Backing up…</> : 'Back up now'}
                </button>
                {backup.result && <p style={{ marginTop: 8, fontSize: 12, color: backup.ok ? 'var(--bullish)' : 'var(--bearish)' }}>{backup.result}</p>}
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}
