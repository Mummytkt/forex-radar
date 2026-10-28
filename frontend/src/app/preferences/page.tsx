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

type Key = 'alertExternal' | 'alertInternal' | 'newsAlerts' | 'alertOrigin' | 'contInline' | 'contBreaker' | 'contOc' | 'contRealign' | 'contEngulfing' | 'dailyEngulfing' | 'h4Fvg' | 'h4OcFormed' | 'dailyOcFormed' | 'ocAfterRetest'
type Status = 'idle' | 'saving' | 'saved' | 'error'

const TYPES: { key: Key; label: string; desc: string; group?: string }[] = [
  { key: 'alertOrigin', group: 'Origin', label: 'Origin alerts', desc: 'The first confirmation of a Daily setup: a Daily reaction followed by an H4 break. External / Internal below choose which kinds.' },
  { key: 'alertExternal', label: 'External breakouts', desc: 'Bias confirmed by an H4 close beyond the last structure formed before price reached the daily level. The standard alert.' },
  { key: 'alertInternal', label: 'Internal breakouts', desc: 'Earlier confirmation from an H4 structure formed after price reacted at the daily level. Off by default. While it is off you also get no continuations of an Internal setup.' },
  { key: 'contInline', group: 'Continuations', label: 'H4 breakout in line', desc: 'A new H4 breakout in the Daily direction while H4 is in line with the Daily.' },
  { key: 'contBreaker', label: 'H4 Breaker retest', desc: 'The first time price comes back to the H4 Breaker, touches it exactly and closes beyond it. Only the first touch counts; after that the Breaker is used.' },
  { key: 'contOc', label: 'H4 OC reaction', desc: 'Price rejects an H4 OC level in the Daily direction.' },
  { key: 'ocAfterRetest', label: 'H4 OC only after a retest that held', desc: 'On: H4 OC rejections and "H4 OC has formed" only come once, after the latest H4 breakout in line, an H4 candle has touched the H4 Breaker or an H4 V-shape (A-shape for sells) of the breakout leg and closed back beyond it. Each new H4 breakout in line starts over. Off (default): every one, as before.' },
  { key: 'contRealign', label: 'Daily reaction + H4 breakout', desc: 'Every fresh reaction at a Daily level followed by an H4 breakout: while H4 is aligned, and when it brings H4 back in line.' },
  { key: 'contEngulfing', label: 'H4 engulfing', desc: 'An H4 candle that covers the previous opposite candle, in the Daily direction. Choose which kind below.' },
  { key: 'dailyEngulfing', label: 'Daily engulfing', desc: 'Only the pair and "Daily buy engulfing candle has formed" (or "Daily sell ..."): a Daily candle covered the previous opposite Daily candle, in the current Daily direction. A notification, not an entry signal. Sent at the Daily close. Choose which kind below.' },
  { key: 'h4Fvg', group: 'Liquidity', label: 'H4 FVG after breakout', desc: 'Only the pair and "H4 FVG candle after breakout has formed": the H4 candle right after an H4 breakout in line with the Daily left a fair value gap. A liquidity marker, not a buy or sell signal. Off unless you switch it on.' },
  { key: 'h4OcFormed', group: 'OC formed', label: 'H4 OC formed', desc: 'Only the pair and "H4 OC has formed": the last two H4 candles both closed in the Daily direction, after the Origin while H4 is in line. A notification, not a buy or sell signal. Off unless you switch it on.' },
  { key: 'dailyOcFormed', label: 'Daily OC formed', desc: 'Only the pair and "Daily OC has formed": the last two Daily candles both closed in the current Daily direction. A notification, not a buy or sell signal. Sent at the Daily close. Off unless you switch it on.' },
  { key: 'newsAlerts', group: 'News', label: 'High-impact news', desc: 'A morning summary (07:00 WAT) of the high-impact economic news for the currencies in your pairs, plus a reminder 30 minutes before each release.' },
]

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<Record<Key, boolean> | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [status, setStatus] = useState<Record<Key, Status>>({ alertExternal: 'idle', alertInternal: 'idle', newsAlerts: 'idle', alertOrigin: 'idle', contInline: 'idle', contBreaker: 'idle', contOc: 'idle', contRealign: 'idle', contEngulfing: 'idle', dailyEngulfing: 'idle', h4Fvg: 'idle', h4OcFormed: 'idle', dailyOcFormed: 'idle', ocAfterRetest: 'idle' })

  const { user } = useAuth()
  useEffect(() => { markOnboarding(user?.id, 'prefs') }, [user?.id])

  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(d => setPrefs({ alertExternal: !!d.alertExternal, alertInternal: !!d.alertInternal, newsAlerts: d.newsAlerts !== false,
        alertOrigin: d.alertOrigin !== false, contInline: d.contInline !== false, contBreaker: d.contBreaker !== false,
        contOc: d.contOc !== false, contRealign: d.contRealign !== false, contEngulfing: d.contEngulfing !== false, dailyEngulfing: d.dailyEngulfing !== false, h4Fvg: d.h4Fvg === true,
        h4OcFormed: d.h4OcFormed === true, dailyOcFormed: d.dailyOcFormed === true, ocAfterRetest: d.ocAfterRetest === true }))
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

  const bothOff = prefs && prefs.alertOrigin && !prefs.alertExternal && !prefs.alertInternal

  // Which H4 engulfings: covers the wick (default), covers the body only, or both
  const [engulf, setEngulf] = useState<'wick' | 'body' | 'both'>('wick')
  const [dEngulf, setDEngulf] = useState<'wick' | 'body' | 'both'>('wick')   // the same choice for the Daily engulfing
  useEffect(() => {
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        if (d && ['wick', 'body', 'both'].includes(d.engulfMode)) setEngulf(d.engulfMode)
        if (d && ['wick', 'body', 'both'].includes(d.dEngulfMode)) setDEngulf(d.dEngulfMode)
      })
      .catch(() => {})
  }, [])
  const chooseEngulf = async (v: 'wick' | 'body' | 'both') => {
    const previous = engulf
    setEngulf(v)
    try {
      const r = await fetch(`${API_BASE}/api/preferences`, { method: 'PATCH', headers: authHeaders(), body: JSON.stringify({ engulfMode: v }) })
      if (!r.ok) throw new Error()
    } catch { setEngulf(previous) }
  }
  const chooseDEngulf = async (v: 'wick' | 'body' | 'both') => {
    const previous = dEngulf
    setDEngulf(v)
    try {
      const r = await fetch(`${API_BASE}/api/preferences`, { method: 'PATCH', headers: authHeaders(), body: JSON.stringify({ dEngulfMode: v }) })
      if (!r.ok) throw new Error()
    } catch { setDEngulf(previous) }
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
      <TopBar title="Alert Filters" subtitle="Choose which bias confirmations reach your Telegram" />
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
              ['full', 'Full', 'Every part explained: the Daily breakout, the reaction, the H4 confirmation and why.'],
              ['short', 'Short', 'Straight to the point: alert type, Daily breakout, reaction, H4 confirmation and reason.'],
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
                {key === 'contEngulfing' && prefs.contEngulfing && (
                  <div style={{ padding: '0 20px 14px', display: 'flex', gap: 6, flexWrap: 'wrap', borderBottom: '1px solid var(--border)' }}>
                    {([['wick', 'Covers the wick'], ['body', 'Covers the body only'], ['both', 'Both']] as const).map(([v, name]) => (
                      <button key={v} onClick={() => chooseEngulf(v)}
                        style={{ padding: '5px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                          border: `1px solid ${engulf === v ? 'var(--accent)' : 'var(--border)'}`,
                          background: engulf === v ? 'var(--accent-bg)' : 'transparent',
                          color: engulf === v ? 'var(--accent-hover)' : 'var(--text-secondary)' }}>
                        {engulf === v ? '✓ ' : ''}{name}
                      </button>
                    ))}
                  </div>
                )}
                {key === 'dailyEngulfing' && prefs.dailyEngulfing && (
                  <div style={{ padding: '0 20px 14px', display: 'flex', gap: 6, flexWrap: 'wrap', borderBottom: '1px solid var(--border)' }}>
                    {([['wick', 'Covers the wick'], ['body', 'Covers the body only'], ['both', 'Both']] as const).map(([v, name]) => (
                      <button key={v} onClick={() => chooseDEngulf(v)}
                        style={{ padding: '5px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                          border: `1px solid ${dEngulf === v ? 'var(--accent)' : 'var(--border)'}`,
                          background: dEngulf === v ? 'var(--accent-bg)' : 'transparent',
                          color: dEngulf === v ? 'var(--accent-hover)' : 'var(--text-secondary)' }}>
                        {dEngulf === v ? '✓ ' : ''}{name}
                      </button>
                    ))}
                  </div>
                )}
                </div>
              ))}

              {bothOff && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '12px 20px', background: 'var(--warning-bg)', fontSize: 12, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)' }}>
                  <AlertTriangle size={14} color="var(--warning)" style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>Both are off, so you won&apos;t receive new Origin confirmations. Continuation alerts still come through.</span>
                </div>
              )}

              <div style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                Continuation alerts follow the setup's latest H4 confirmation (its Origin, or a later "H4 back in line"): you get them only if you received that confirmation's type, External or Internal.
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
