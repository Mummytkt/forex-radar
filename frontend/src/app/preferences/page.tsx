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

type Key = 'alertExternal' | 'alertInternal'
type Status = 'idle' | 'saving' | 'saved' | 'error'

const TYPES: { key: Key; label: string; desc: string }[] = [
  { key: 'alertExternal', label: 'External breakouts', desc: 'Bias confirmed by an H4 close beyond the last structure formed before price reached the daily level. The standard alert.' },
  { key: 'alertInternal', label: 'Internal breakouts', desc: 'Earlier confirmation from an H4 structure formed after price reacted at the daily level.' },
]

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<Record<Key, boolean> | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [status, setStatus] = useState<Record<Key, Status>>({ alertExternal: 'idle', alertInternal: 'idle' })

  const { user } = useAuth()
  useEffect(() => { markOnboarding(user?.id, 'prefs') }, [user?.id])

  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(d => setPrefs({ alertExternal: !!d.alertExternal, alertInternal: !!d.alertInternal }))
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

  const bothOff = prefs && !prefs.alertExternal && !prefs.alertInternal

  return (
    <>
      <TopBar title="Preferences" subtitle="Choose which bias confirmations reach your Telegram" />
      <main className="page-padded" style={{ flex: 1, padding: '24px', maxWidth: 720, display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Telegram delivery */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Telegram delivery</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.6 }}>
              Choose which Origin confirmations are sent to your Telegram. Changes save to your account straight away and only affect you.
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
              {TYPES.map(({ key, label, desc }) => (
                <div key={key} style={{
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
              ))}

              {bothOff && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '12px 20px', background: 'var(--warning-bg)', fontSize: 12, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}>
                  <AlertTriangle size={14} color="var(--warning)" style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>Both are off, so you won&apos;t receive new Origin confirmations. Continuation alerts still come through.</span>
                </div>
              )}

              <div style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Continuation alerts (breaker retest, OC reaction, breakout continuation) always reach you. They follow an Origin you already received.
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
              Pick which pairs reach your Telegram in Settings. To filter what you see in History, use the Buy / Sell filter on the History page.
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
