'use client'
// Requests (owner, 2026-11-25): it replaced Job Hunt in the menu. Every "Test my strategy" request from the public
// page, from New to Delivered, with her notes. Job applications stay saved at /job-hunt.
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { Inbox, Copy, Trash2, ExternalLink, ChevronDown } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'

interface Req { id: number; created_at: string; name: string; contact: string; role: string; markets: string; timeframes: string
  strategy: string; backtest_now: string; goal: string; status: string; notes: string }
const STATUS: [string, string, string][] = [['new', 'New', '#eab308'], ['contacted', 'Contacted', '#3b82f6'], ['call', 'Call booked', '#8b5cf6'],
  ['building', 'Building', '#f97316'], ['delivered', 'Delivered', '#22c55e'], ['closed', 'Closed', '#6b7280']]
const api = (p: string, o: RequestInit = {}) => {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${p}`, { ...o, headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) } })
}
const PUBLIC_PAGE = typeof window !== 'undefined' ? `${window.location.origin}/test-my-strategy` : '/test-my-strategy'

function reachLink(contact: string): string | null {
  const c = contact.trim()
  if (/^\S+@\S+\.\S+$/.test(c)) return `mailto:${c}`
  const digits = c.replace(/[^\d+]/g, '')
  if (/^\+?\d{8,15}$/.test(digits)) return `https://wa.me/${digits.replace(/^\+/, '')}`
  if (/^@?\w{4,}$/.test(c)) return `https://t.me/${c.replace(/^@/, '')}`
  return null
}

export default function RequestsPage() {
  const [list, setList] = useState<Req[] | null>(null)
  const [tab, setTab] = useState<'open' | 'all'>('open')
  const [open, setOpen] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)
  const load = useCallback(async () => {
    const r = await api('/api/strategy-requests')
    setList(r.ok ? (await r.json()).requests : [])
  }, [])
  useEffect(() => { load() }, [load])
  const patch = async (id: number, body: Partial<Req>) => {
    await api(`/api/strategy-requests/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
    load()
  }
  const remove = async (r: Req) => {
    if (!confirm(`Delete ${r.name}'s request? This can't be undone.`)) return
    await api(`/api/strategy-requests/${r.id}`, { method: 'DELETE' })
    load()
  }
  const all = list ?? []
  const count = (s: string) => all.filter(r => r.status === s).length
  const shown = tab === 'open' ? all.filter(r => !['delivered', 'closed'].includes(r.status)) : all
  const tile = (label: string, v: number, c: string) => (
    <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: '14px 16px', background: 'var(--card)' }}>
      <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 900, color: c, marginTop: 4 }}>{v}</div>
    </div>
  )
  const pill = (on: boolean): React.CSSProperties => ({ padding: '7px 14px', borderRadius: 9, fontWeight: 700, fontSize: 13, cursor: 'pointer',
    border: '1px solid var(--border)', background: on ? 'var(--accent)' : 'transparent', color: on ? 'white' : 'var(--text-secondary)' })
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <TopBar title="Requests" subtitle="People who want their strategy tested" />
      <main style={{ maxWidth: 1100, padding: '20px 24px', display: 'grid', gap: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
          {tile('New', count('new'), '#eab308')}
          {tile('In progress', count('contacted') + count('call') + count('building'), '#3b82f6')}
          {tile('Delivered', count('delivered'), '#22c55e')}
          {tile('All requests', all.length, 'var(--text-primary)')}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', border: '1px dashed var(--border)', borderRadius: 12, padding: '10px 14px', fontSize: 13 }}>
          <span style={{ color: 'var(--text-secondary)' }}>Your public page (link it from your bios):</span>
          <a href="/test-my-strategy" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            /test-my-strategy <ExternalLink size={13} /></a>
          <button onClick={() => { navigator.clipboard?.writeText(PUBLIC_PAGE); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
            style={{ ...pill(false), padding: '5px 10px', display: 'inline-flex', alignItems: 'center', gap: 5 }}><Copy size={12} /> {copied ? 'Copied' : 'Copy link'}</button>
          <Link href="/job-hunt" style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 12 }}>Old job applications →</Link>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={pill(tab === 'open')} onClick={() => setTab('open')}>Open</button>
          <button style={pill(tab === 'all')} onClick={() => setTab('all')}>All</button>
        </div>
        {list === null ? <p style={{ color: 'var(--text-muted)' }}>Loading…</p> : shown.length === 0 ? (
          <div style={{ border: '1px solid var(--border)', borderRadius: 14, padding: '40px 20px', textAlign: 'center', background: 'var(--card)' }}>
            <Inbox size={30} color="var(--text-muted)" />
            <p style={{ fontWeight: 700, margin: '10px 0 4px' }}>No requests yet</p>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>Share your page in your bio and posts; each request lands here and on Telegram.</p>
          </div>
        ) : shown.map(r => {
          const st = STATUS.find(s => s[0] === r.status) ?? STATUS[0]
          const isOpen = open === r.id
          const link = reachLink(r.contact)
          return (
            <div key={r.id} style={{ border: '1px solid var(--border)', borderLeft: `4px solid ${st[2]}`, borderRadius: 12, background: 'var(--card)', padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <button onClick={() => setOpen(isOpen ? null : r.id)} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none',
                  cursor: 'pointer', color: 'var(--text-primary)', padding: 0, textAlign: 'left', flex: 1, minWidth: 220 }}>
                  <ChevronDown size={15} style={{ transform: isOpen ? 'none' : 'rotate(-90deg)', transition: 'transform 0.15s' }} />
                  <b style={{ fontSize: 15 }}>{r.name}</b>
                  <span style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                    {r.role}{r.markets ? ` · ${r.markets}` : ''} · {new Date(r.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                  </span>
                </button>
                {link ? <a href={link} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 700 }}>{r.contact}</a>
                  : <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{r.contact}</span>}
                <select value={r.status} onChange={e => patch(r.id, { status: e.target.value })}
                  style={{ padding: '6px 8px', borderRadius: 8, border: `1px solid ${st[2]}`, background: 'var(--bg)', color: st[2], fontWeight: 700 }}>
                  {STATUS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
                <button onClick={() => remove(r)} title="Delete" style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 7, padding: 6, cursor: 'pointer', color: 'var(--bearish)' }}><Trash2 size={13} /></button>
              </div>
              {isOpen && (
                <div style={{ display: 'grid', gap: 10, marginTop: 12, fontSize: 14, lineHeight: 1.6 }}>
                  {r.timeframes && <div><b>Timeframes:</b> {r.timeframes}</div>}
                  <div><b>Strategy and entry rules:</b><div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)' }}>{r.strategy}</div></div>
                  {r.backtest_now && <div><b>How they test today:</b> <span style={{ color: 'var(--text-secondary)' }}>{r.backtest_now}</span></div>}
                  {r.goal && <div><b>Most wants to know:</b> <span style={{ color: 'var(--text-secondary)' }}>{r.goal}</span></div>}
                  <label style={{ display: 'grid', gap: 5, fontWeight: 700, fontSize: 13 }}>Your notes
                    <textarea defaultValue={r.notes} onBlur={e => e.target.value !== r.notes && patch(r.id, { notes: e.target.value })}
                      placeholder="Call notes, price agreed, next step…" style={{ minHeight: 80, padding: 10, borderRadius: 9, border: '1px solid var(--border)',
                        background: 'var(--bg)', color: 'var(--text-primary)', fontFamily: 'inherit', fontSize: 14 }} />
                  </label>
                </div>
              )}
            </div>
          )
        })}
      </main>
    </div>
  )
}
