'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { CheckCircle2, Circle, X, ArrowRight } from 'lucide-react'
import { API_BASE } from '@/lib/api'

export interface Onboarding {
  telegram_linked: boolean; pairs_chosen: boolean; alerts_reviewed: boolean; has_videos: boolean
}

/** Per-viewer flags for steps the server can't see (all keyed by user id). */
export const onbKey = (uid: number | string, what: 'dismissed' | 'video' | 'prefs') => `mbp_onb_${what}_${uid}`
export function markOnboarding(uid: number | string | undefined, what: 'video' | 'prefs') {
  if (uid === undefined) return
  try { localStorage.setItem(onbKey(uid, what), '1') } catch {}
}
const flag = (k: string) => { try { return localStorage.getItem(k) === '1' } catch { return false } }

/** First-login setup checklist for subscribers. Ticks itself off; hides when done or dismissed. */
export default function OnboardingChecklist({ uid, data }: { uid: number; data: Onboarding }) {
  const [dismissed, setDismissed] = useState(true)   // start hidden to avoid a flash before storage is read
  const [watched, setWatched] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const [tgLink, setTgLink] = useState<string | null>(null)

  useEffect(() => {
    setDismissed(flag(onbKey(uid, 'dismissed')))
    setWatched(flag(onbKey(uid, 'video')))
    setReviewed(flag(onbKey(uid, 'prefs')))
  }, [uid])

  useEffect(() => {
    if (data.telegram_linked) return
    const t = localStorage.getItem('mbp_token')
    fetch(`${API_BASE}/api/telegram/connection`, { headers: t ? { Authorization: `Bearer ${t}` } : {} })
      .then(r => (r.ok ? r.json() : null)).then(d => d?.link_url && setTgLink(d.link_url)).catch(() => {})
  }, [data.telegram_linked])

  const steps = [
    { done: data.telegram_linked, title: 'Link your Telegram', body: 'Alerts are delivered there. Takes one tap.',
      action: tgLink ? { href: tgLink, label: 'Connect Telegram', external: true } : { href: '/settings', label: 'Open Settings' } },
    { done: data.pairs_chosen, title: 'Choose your pairs', body: 'Only get alerts for the markets you trade.',
      action: { href: '/settings', label: 'Choose pairs' } },
    { done: data.alerts_reviewed || reviewed, title: 'Pick which confirmations you want', body: 'External, internal, or both.',
      action: { href: '/preferences', label: 'Open Alert Filters' } },
    ...(data.has_videos ? [{ done: watched, title: 'Watch the intro video', body: 'See how a bias call is built, start to finish.',
      action: { href: '/strategy', label: 'Watch' } }] : []),
  ]
  const doneCount = steps.filter(s => s.done).length
  if (dismissed || doneCount === steps.length) return null

  const dismiss = () => { try { localStorage.setItem(onbKey(uid, 'dismissed'), '1') } catch {} ; setDismissed(true) }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--accent)40', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Get set up</h2>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{doneCount} of {steps.length} done</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div aria-hidden style={{ width: 120, height: 6, borderRadius: 99, background: 'var(--border)', overflow: 'hidden' }}>
            <div style={{ width: `${(doneCount / steps.length) * 100}%`, height: '100%', background: 'var(--accent)', borderRadius: 99, transition: 'width 0.3s' }} />
          </div>
          <button onClick={dismiss} aria-label="Hide setup checklist" title="Hide"
            style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid var(--border)', background: 'var(--card-hover)', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <X size={13} />
          </button>
        </div>
      </div>
      <div>
        {steps.map(s => (
          <div key={s.title} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px', borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
            {s.done ? <CheckCircle2 size={18} color="var(--bullish)" style={{ flexShrink: 0 }} /> : <Circle size={18} color="var(--text-muted)" style={{ flexShrink: 0 }} />}
            <div style={{ flex: '1 1 200px', minWidth: 0 }}>
              <p style={{ fontWeight: 600, fontSize: 13, color: s.done ? 'var(--text-secondary)' : 'var(--text-primary)', textDecoration: s.done ? 'line-through' : 'none' }}>{s.title}</p>
              {!s.done && <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{s.body}</p>}
            </div>
            {!s.done && ('external' in s.action && s.action.external
              ? <a href={s.action.href} target="_blank" rel="noopener noreferrer" style={actionStyle}>{s.action.label} <ArrowRight size={12} /></a>
              : <Link href={s.action.href} style={actionStyle}>{s.action.label} <ArrowRight size={12} /></Link>)}
          </div>
        ))}
      </div>
    </div>
  )
}

const actionStyle: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600,
  background: 'var(--accent)', color: 'white', textDecoration: 'none', flexShrink: 0,
}
