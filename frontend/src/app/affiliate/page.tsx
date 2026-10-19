'use client'
import { useState, useEffect } from 'react'
import { Gift, Copy, Check, Link2, Hash, TrendingUp, Clock, Wallet, Users } from 'lucide-react'
import TopBar from '@/components/TopBar'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080'

function apiFetch(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers ?? {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) },
  })
}

interface Totals { pending: number; available: number; paid: number; lifetime: number }
interface Commission { customer_email: string; rate: number; amount_usd: number; status: string; created_at: string }
interface AffiliateData {
  joined: boolean
  code?: string
  link?: string
  paid_customers?: number
  next_rate?: number
  totals?: Totals
  recent?: Commission[]
}

function CopyField({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try { await navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1600) } catch {}
  }
  return (
    <div>
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 7 }}>
        <Icon size={13} /> {label}
      </label>
      <div style={{ display: 'flex', gap: 8 }}>
        <input readOnly value={value} style={{ flex: 1, padding: '10px 12px', borderRadius: 9, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-primary)', fontSize: 13, fontFamily: 'monospace', outline: 'none' }} />
        <button onClick={copy} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '0 16px', borderRadius: 9, border: 'none', cursor: 'pointer', background: copied ? 'var(--bullish)' : 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600 }}>
          {copied ? <><Check size={14} /> Copied</> : <><Copy size={14} /> Copy</>}
        </button>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string; icon: React.ElementType; color: string }) {
  return (
    <div style={{ background: `${color}15`, border: `1px solid ${color}44`, borderRadius: 14, padding: '16px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>{label}</span>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={14} color="#fff" />
        </div>
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color }}>{value}</div>
    </div>
  )
}

export default function AffiliatePage() {
  const [data, setData] = useState<AffiliateData | null>(null)
  const [joining, setJoining] = useState(false)

  const load = async () => {
    try { const r = await apiFetch('/api/affiliate'); setData(await r.json()) } catch { setData({ joined: false }) }
  }
  useEffect(() => { load() }, [])

  const join = async () => {
    setJoining(true)
    try { const r = await apiFetch('/api/affiliate/join', { method: 'POST' }); setData(await r.json()) } catch {}
    setJoining(false)
  }

  return (
    <>
      <TopBar title="Refer & Earn" subtitle="Earn a share of every subscriber you bring in" />
      <main style={{ flex: 1, width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {!data && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>}

        {data && !data.joined && (
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '28px' }}>
            <div style={{ width: 48, height: 48, borderRadius: 13, background: 'linear-gradient(135deg,#ec4899,#a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <Gift size={22} color="#fff" />
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 8 }}>Turn your network into income</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 20, maxWidth: 560 }}>
              Share the Bias Pointer with the traders around you and earn on every one who subscribes —
              for as long as they stay. Get your own link and code in one click.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 22px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                ['You earn', '10% of every payment from your first 10 subscribers, then 15% from the 11th onward — recurring, for as long as each keeps paying.'],
                ['You get paid', 'Each commission clears 7 days after your subscriber pays, then moves to your available balance for payout.'],
                ['Keep it honest', 'Remind anyone you share with that trading carries risk — never promise guaranteed profit.'],
              ].map(([h, b]) => (
                <li key={h} style={{ display: 'flex', gap: 10 }}>
                  <Check size={16} color="var(--bullish)" style={{ flexShrink: 0, marginTop: 2 }} />
                  <span style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}><strong style={{ color: 'var(--text-primary)' }}>{h}:</strong> {b}</span>
                </li>
              ))}
            </ul>
            <button onClick={join} disabled={joining} style={{ padding: '12px 24px', borderRadius: 11, border: 'none', cursor: joining ? 'not-allowed' : 'pointer', background: 'var(--accent)', color: '#fff', fontSize: 14, fontWeight: 700, opacity: joining ? 0.7 : 1 }}>
              {joining ? 'Setting up…' : 'Join & get my link'}
            </button>
          </div>
        )}

        {data && data.joined && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14 }}>
              <StatCard label="Available" value={`$${(data.totals?.available ?? 0).toFixed(2)}`} icon={Wallet} color="#10b981" />
              <StatCard label="Pending" value={`$${(data.totals?.pending ?? 0).toFixed(2)}`} icon={Clock} color="#f59e0b" />
              <StatCard label="Lifetime" value={`$${(data.totals?.lifetime ?? 0).toFixed(2)}`} icon={TrendingUp} color="#6366f1" />
              <StatCard label="Subscribers" value={String(data.paid_customers ?? 0)} icon={Users} color="#ec4899" />
            </div>

            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 3 }}>Share & earn</h3>
                <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  Send the <strong>link</strong> to people you refer — it tags them to you automatically. Or give out your <strong>code</strong> for anyone who&apos;d rather type it in at checkout. You&apos;re currently earning <strong>{Math.round((data.next_rate ?? 0.1) * 100)}%</strong> per payment.
                </p>
              </div>
              <CopyField label="Your referral link" value={data.link ?? ''} icon={Link2} />
              <CopyField label="Your referral code" value={data.code ?? ''} icon={Hash} />
            </div>

            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', fontWeight: 700, fontSize: 14 }}>Recent commissions</div>
              {(!data.recent || data.recent.length === 0) ? (
                <div style={{ padding: '36px 24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  No commissions yet. Share your link to get started.
                </div>
              ) : (
                <div>
                  {data.recent.map((c, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderBottom: '1px solid var(--border)' }}>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600 }}>{c.customer_email.replace(/(.{2}).*(@.*)/, '$1•••$2')}</p>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{Math.round(c.rate * 100)}% · {new Date(c.created_at).toLocaleDateString()}</p>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--bullish)' }}>+${c.amount_usd.toFixed(2)}</p>
                        <p style={{ fontSize: 11, color: c.status === 'available' ? 'var(--bullish)' : c.status === 'paid' ? 'var(--text-muted)' : 'var(--warning)', marginTop: 2, textTransform: 'capitalize' }}>{c.status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </>
  )
}
