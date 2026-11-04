'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Check, AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { markOnboarding } from '@/components/OnboardingChecklist'

function authHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {}
  const t = localStorage.getItem('mbp_token')
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

function Toggle({ checked, disabled, onChange }: { checked: boolean; disabled?: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="toggle" style={{ opacity: disabled ? 0.6 : 1 }}>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={e => onChange(e.target.checked)} />
      <div className="toggle-track">
        <div className="toggle-thumb" />
      </div>
    </label>
  )
}

type Key = 'newsAlerts' | 'dailyBreakout' | 'storyCont' | 'storyPullback' | 'storyAgainst'
type Status = 'idle' | 'saving' | 'saved' | 'error'

const TYPES: { key: Key; label: string; desc: string; group?: string }[] = [
  { key: 'dailyBreakout', group: 'Bias alerts', label: 'Daily breakout', desc: 'A Daily candle closed beyond the Daily external high or low. This sets the Daily direction.' },
  { key: 'storyCont', label: 'H4 continuation after the Daily breakout', desc: 'Each H4 continuation in the Daily direction, until the pullback is confirmed.' },
  { key: 'storyPullback', label: 'H4 pullback confirmed', desc: 'An H4 candle closed beyond the pullback line, so H4 is now against the Daily.' },
  { key: 'storyAgainst', label: 'H4 continuation after the pullback', desc: 'Each H4 continuation against the Daily after the pullback, until H4 reverses into the H4 range.' },
  { key: 'newsAlerts', group: 'News', label: 'High-impact news', desc: 'A morning summary (07:00 WAT) of the high-impact economic news for the currencies in your pairs, plus a reminder 30 minutes before each one.' },
]

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<Record<Key, boolean> | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [status, setStatus] = useState<Record<Key, Status>>({ newsAlerts: 'idle', dailyBreakout: 'idle', storyCont: 'idle', storyPullback: 'idle', storyAgainst: 'idle' })

  const { user } = useAuth()
  useEffect(() => { markOnboarding(user?.id, 'prefs') }, [user?.id])

  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(d => setPrefs({ newsAlerts: d.newsAlerts !== false, dailyBreakout: d.dailyBreakout !== false, storyCont: d.storyCont !== false,
        storyPullback: d.storyPullback !== false, storyAgainst: d.storyAgainst !== false }))
      .catch(() => setLoadError(true))
  }, [])

  const change = async (key: Key, value: boolean) => {
    if (!prefs) return
    const previous = prefs[key]
    setPrefs({ ...prefs, [key]: value })
    setStatus(s => ({ ...s, [key]: 'saving' }))
    try {
      const r = await fetch(`${API_BASE}/api/preferences`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({ [key]: value }),
      })
      if (!r.ok) throw new Error()
      setStatus(s => ({ ...s, [key]: 'saved' }))
      setTimeout(() => setStatus(s => (s[key] === 'saved' ? { ...s, [key]: 'idle' } : s)), 2000)
    } catch {
      // Put the switch back so it always shows what is really saved
      setPrefs(p => (p ? { ...p, [key]: previous } : p))
      setStatus(s => ({ ...s, [key]: 'error' }))
    }
  }

  // Message style: the full explanation, or Short (headlines only)
  const [style, setStyle] = useState<'full' | 'short'>('short')
  const [styleStatus, setStyleStatus] = useState<Status>('idle')
  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d && (d.alertStyle === 'short' || d.alertStyle === 'full')) setStyle(d.alertStyle) })
      .catch(() => {})
  }, [])
  const chooseStyle = async (v: 'full' | 'short') => {
    const previous = style
    setStyle(v)
    setStyleStatus('saving')
    try {
      const r = await fetch(`${API_BASE}/api/preferences`, { method: 'PATCH', headers: authHeaders(), body: JSON.stringify({ alertStyle: v }) })
      if (!r.ok) throw new Error()
      setStyleStatus('saved')
      setTimeout(() => setStyleStatus(s => (s === 'saved' ? 'idle' : s)), 2000)
    } catch {
      setStyle(previous)
      setStyleStatus('error')
    }
  }

  return (
    <>
      <TopBar title="Alert Filters" subtitle="Choose which alerts reach your Telegram" />
      <main className="page-padded" style={{ flex: 1, width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Message style */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Message style</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.6 }}>
              How your bias alerts read on Telegram. Short keeps the headline of each part and drops the explanations.
            </p>
          </div>
          <div style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
            {([
              ['full', 'Full', 'Every part explained: what broke, what it means and the level to watch next.'],
              ['short', 'Short', 'Straight to the point: alert type and the levels, without the explanations.'],
            ] as const).map(([v, name, desc]) => (
              <button key={v} onClick={() => chooseStyle(v)} disabled={styleStatus === 'saving'}
                style={{ textAlign: 'left', padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                  border: `1px solid ${style === v ? 'var(--accent)' : 'var(--border)'}`,
                  background: style === v ? 'var(--accent-bg)' : 'transparent', color: 'var(--text-primary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, fontSize: 13 }}>
                  {style === v && <Check size={13} color="var(--accent)" />}{name}
                </span>
                <span style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>{desc}</span>
              </button>
            ))}
          </div>
          <div style={{ padding: '0 20px 12px', minHeight: 18, fontSize: 11, fontWeight: 600 }}>
            {styleStatus === 'saved' && <span style={{ color: 'var(--bullish)' }}>Saved</span>}
            {styleStatus === 'error' && <span style={{ color: 'var(--bearish)' }}>Couldn&apos;t save. Check your connection and try again.</span>}
          </div>
        </div>

        {/* Telegram delivery */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Telegram delivery</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.6 }}>
              Choose which alerts and news reach your Telegram. Changes save to your account straight away and only affect you.
            </p>
          </div>

          {loadError ? (
            <div style={{ padding: '18px 20px', fontSize: 13, color: 'var(--bearish)' }}>
              Couldn&apos;t load your preferences. Refresh the page to try again.
            </div>
          ) : !prefs ? (
            <div style={{ padding: '18px 20px', fontSize: 13, color: 'var(--text-secondary)' }}>Loading…</div>
          ) : (
            <div>
              {TYPES.map(({ key, label, desc, group }) => (
                <div key={key}>
                {group && (
                  <div style={{ padding: '12px 20px 6px', fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>{group}</div>
                )}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
                  padding: '14px 20px', borderBottom: '1px solid var(--border)',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{label}</p>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.6 }}>{desc}</p>
                    <div style={{ minHeight: 18, marginTop: 4, fontSize: 11, fontWeight: 600 }}>
                      {status[key] === 'saving' && (
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <Loader2 size={11} className="spin" /> Saving…
                        </span>
                      )}
                      {status[key] === 'saved' && (
                        <span style={{ color: 'var(--bullish)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <Check size={11} /> Saved
                        </span>
                      )}
                      {status[key] === 'error' && (
                        <span style={{ color: 'var(--bearish)' }}>Couldn&apos;t save. Check your connection and try again.</span>
                      )}
                    </div>
                  </div>
                  <Toggle checked={prefs[key]} disabled={status[key] === 'saving'} onChange={v => change(key, v)} />
                </div>
                </div>
              ))}

              <div style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Inside the H4 range no bias alert is sent. Set the levels you are watching on the <Link href="/price-alerts" style={{ color: 'var(--accent-hover)' }}>Price Alerts</Link> page and tick the entry formations you want to hear about.
              </div>
            </div>
          )}
        </div>

        {/* Pairs live in Settings */}
        <div style={{
          background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12,
          padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 14, flexWrap: 'wrap',
        }}>
          <div style={{ minWidth: 0, flex: '1 1 260px' }}>
            <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Pairs</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.6 }}>
              Pick which pairs reach your Telegram in Settings. To filter what you see in the Signal Log, use its Buy / Sell filter.
            </p>
          </div>
          <Link href="/settings" style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8,
            fontSize: 12, fontWeight: 600, background: 'var(--accent)', color: 'white', textDecoration: 'none', flexShrink: 0,
          }}>
            My Instruments <ArrowRight size={13} />
          </Link>
        </div>
      </main>
    </>
  )
}
