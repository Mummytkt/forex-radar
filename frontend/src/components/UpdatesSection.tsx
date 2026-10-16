'use client'
import { useEffect, useState, useCallback } from 'react'
import { mutate } from 'swr'
import { Megaphone, Trash2, Send, Loader2 } from 'lucide-react'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useTimezone } from '@/lib/timezone'

interface Update { id: number; title: string; body: string; sent_telegram: number; created_at: string }

export const UNREAD_KEY = '/api/announcements/unread'

function api(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}), 'Content-Type': 'application/json' },
  })
}

/** Render text safely with clickable links and kept line breaks. */
function RichText({ text }: { text: string }) {
  const parts = text.split(/(https?:\/\/[^\s]+)/g)
  return (
    <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', marginTop: 6 }}>
      {parts.map((p, i) => /^https?:\/\//.test(p)
        ? <a key={i} href={p} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>{p}</a>
        : <span key={i}>{p}</span>)}
    </p>
  )
}

/** Owner → subscriber updates. Owner composes and deletes; subscribers read, new ones marked. */
export default function UpdatesSection() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const { fmtDate } = useTimezone()
  const [items, setItems] = useState<Update[] | null>(null)
  const [seenBefore, setSeenBefore] = useState(0)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [toTelegram, setToTelegram] = useState(false)
  const [posting, setPosting] = useState(false)
  const [msg, setMsg] = useState('')
  const [confirmDel, setConfirmDel] = useState<number | null>(null)

  const load = useCallback(async () => {
    const r = await api('/api/announcements').catch(() => null)
    if (!r || !r.ok) { setItems([]); return }
    const d = await r.json()
    setItems(d.items)
    setSeenBefore(d.last_read_id)
    // Mark everything shown as read; keep the "New" tags for this visit.
    const newest = d.items[0]?.id ?? 0
    if (!isOwner && newest > d.last_read_id) {
      await api('/api/announcements/read', { method: 'POST', body: JSON.stringify({ last_id: newest }) }).catch(() => {})
      mutate(UNREAD_KEY, { unread: 0 }, false)
    }
  }, [isOwner])

  useEffect(() => { if (user) load() }, [user, load])

  const post = async () => {
    setPosting(true); setMsg('')
    try {
      const r = await api('/api/announcements', { method: 'POST', body: JSON.stringify({ title, body, send_telegram: toTelegram }) })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail || 'Could not post the update.')
      setTitle(''); setBody(''); setToTelegram(false)
      setMsg(toTelegram
        ? `Posted, and sent to ${d.telegram_sent} of ${d.telegram_targets} subscriber${d.telegram_targets === 1 ? '' : 's'} on Telegram.`
        : 'Posted. Subscribers will see a badge on Tutorials.')
      load()
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : 'Could not post the update.')
    } finally {
      setPosting(false)
    }
  }

  const remove = async (id: number) => {
    if (confirmDel !== id) { setConfirmDel(id); setTimeout(() => setConfirmDel(c => (c === id ? null : c)), 4000); return }
    setConfirmDel(null)
    const r = await api(`/api/announcements/${id}`, { method: 'DELETE' })
    if (r.ok) setItems(xs => (xs ?? []).filter(x => x.id !== id))
  }

  // Subscribers don't see an empty section.
  if (!isOwner && items !== null && items.length === 0) return null

  const input: React.CSSProperties = { width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-primary)', fontSize: 13, outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Megaphone size={15} color="var(--accent-hover)" />
        <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Updates</h2>
        {isOwner && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>· messages to your subscribers</span>}
      </div>

      {isOwner && (
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input id="update-title" value={title} onChange={e => setTitle(e.target.value)} maxLength={120} placeholder="Title, e.g. New tutorial: H4 breaker retests" style={input} />
          <textarea id="update-body" value={body} onChange={e => setBody(e.target.value)} maxLength={3500} rows={4}
            placeholder="Your message. Links (YouTube, TradingView) become clickable." style={{ ...input, resize: 'vertical', lineHeight: 1.6 }} />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <label htmlFor="update-tg" style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input id="update-tg" type="checkbox" checked={toTelegram} onChange={e => setToTelegram(e.target.checked)} />
              Also send to subscribers&apos; Telegram
            </label>
            <button onClick={post} disabled={posting || !title.trim() || !body.trim()}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer', background: 'var(--accent)', color: 'white', opacity: posting || !title.trim() || !body.trim() ? 0.55 : 1 }}>
              {posting ? <><Loader2 size={13} className="spin" /> Posting…</> : <><Send size={13} /> Post update</>}
            </button>
          </div>
          {msg && <p style={{ fontSize: 12, color: msg.startsWith('Could') || msg.startsWith('Add') || msg.startsWith('Keep') ? 'var(--bearish)' : 'var(--bullish)' }}>{msg}</p>}
        </div>
      )}

      <div>
        {items === null && <p style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-secondary)' }}>Loading…</p>}
        {items && items.length === 0 && (
          <p style={{ padding: '16px 20px', fontSize: 13, color: 'var(--text-muted)' }}>No updates yet. What you post here appears on every subscriber&apos;s Tutorials page.</p>
        )}
        {items?.map(u => {
          const isNew = !isOwner && u.id > seenBefore
          return (
            <div key={u.id} style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: isNew ? 'var(--accent-bg)' : 'transparent' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{u.title}</span>
                    {isNew && <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.05em', padding: '2px 7px', borderRadius: 999, background: 'var(--accent)', color: 'white' }}>NEW</span>}
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {fmtDate(u.created_at)}{isOwner && u.sent_telegram ? ' · also sent to Telegram' : ''}
                  </span>
                </div>
                {isOwner && (
                  <button onClick={() => remove(u.id)} title="Delete update"
                    style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, flexShrink: 0,
                      background: confirmDel === u.id ? 'var(--bearish)' : 'var(--bearish-bg)', color: confirmDel === u.id ? 'white' : 'var(--bearish)' }}>
                    <Trash2 size={11} /> {confirmDel === u.id ? 'Tap again' : 'Delete'}
                  </button>
                )}
              </div>
              <RichText text={u.body} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
