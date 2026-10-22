'use client'
import { useState, useEffect } from 'react'
import { Send, CheckCircle, XCircle, User, Save, Info, Check, Search, RefreshCw } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { loadUserName, saveUserName } from '@/lib/preferences'
import { useAuth } from '@/lib/auth'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080'

function apiFetch(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers ?? {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) },
  })
}

const ALL_INSTRUMENTS: Record<string, string[]> = {
  'Majors': ['EUR/USD','GBP/USD','USD/JPY','USD/CHF','USD/CAD','AUD/USD','NZD/USD'],
  'EUR Crosses': ['EUR/JPY','EUR/GBP','EUR/AUD','EUR/CAD','EUR/NZD','EUR/CHF'],
  'GBP Crosses': ['GBP/JPY','GBP/AUD','GBP/CAD','GBP/NZD','GBP/CHF'],
  'Commodity Crosses': ['AUD/JPY','AUD/CAD','AUD/NZD','AUD/CHF','NZD/JPY','NZD/CAD','NZD/CHF','CAD/JPY','CAD/CHF','CHF/JPY'],
  'Metals': ['XAU/USD', 'XAG/USD'],
  'Energy': ['WTI/USD'],
  'Indices': ['US30','NAS100','SPX500','UK100','GER40','JPN225'],
  'Crypto': ['BTC/USD','ETH/USD','SOL/USD','BNB/USD','XRP/USD','ADA/USD','DOGE/USD','LTC/USD','TRX/USD','SUI/USD','AVAX/USD','LINK/USD','ZEC/USD','NEAR/USD','HYPE/USD','BCH/USD','DOT/USD','UNI/USD','AAVE/USD','TAO/USD','INJ/USD','SEI/USD','ICP/USD','ATOM/USD','XLM/USD','ETC/USD','FIL/USD','ARB/USD','OP/USD','ASTER/USD'],
}

const SYNTH_CAT = 'Deriv synthetics'

function Section({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
        <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>{title}</h2>
        {desc && <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{desc}</p>}
      </div>
      <div>{children}</div>
    </div>
  )
}

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '13px 20px', borderBottom: '1px solid var(--border)' }}>
      <div>
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{label}</p>
        {note && <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>{note}</p>}
      </div>
      <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-secondary)', marginTop: 1 }}>{value}</span>
    </div>
  )
}

function InstrumentManager() {
  const [enabled, setEnabled] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState<'ok' | 'fail' | null>(null)
  const [search, setSearch] = useState('')
  // Deriv synthetic indices on the platform (they register when their chart first reports)
  const [synth, setSynth] = useState<string[]>([])
  const cats: Record<string, string[]> = synth.length ? { ...ALL_INSTRUMENTS, [SYNTH_CAT]: synth } : ALL_INSTRUMENTS

  const load = async () => {
    setLoading(true)
    try {
      const rc = await apiFetch('/api/config/instruments')
      if (rc.ok) setSynth(((await rc.json()).synthetics ?? []) as string[])
    } catch { /* ignore */ }
    try {
      const r = await apiFetch('/api/user/instruments')
      const data = await r.json()
      // null = no personal list saved yet → every standard pair selected (synthetics are opt-in)
      if (data.instruments === null || data.instruments === undefined) {
        setEnabled(Object.values(ALL_INSTRUMENTS).flat())
      } else {
        setEnabled(data.instruments)
      }
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const isOn = (p: string) => enabled.includes(p)

  const toggle = (p: string) =>
    setEnabled(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p])

  const toggleCat = (cat: string) => {
    const pairs = cats[cat]
    const allOn = pairs.every(p => isOn(p))
    if (allOn) setEnabled(prev => prev.filter(p => !pairs.includes(p)))
    else setEnabled(prev => [...new Set([...prev, ...pairs])])
  }

  const save = async () => {
    if (enabled.length === 0) return
    setSaving(true)
    setSaveResult(null)
    try {
      const r = await apiFetch('/api/user/instruments', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruments: enabled }),
      })
      setSaveResult(r.ok ? 'ok' : 'fail')
    } catch { setSaveResult('fail') }
    setSaving(false)
    setTimeout(() => setSaveResult(null), 4000)
  }

  const totalAvailable = Object.values(cats).flat().length
  const filtered = Object.entries(cats)
    .map(([cat, pairs]) => ({ cat, pairs: search ? pairs.filter(p => p.replace('/', '').toLowerCase().includes(search.toLowerCase())) : pairs }))
    .filter(({ pairs }) => pairs.length > 0)

  return (
    <div>
      <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 11px', flex: 1, maxWidth: 260 }}>
          <Search size={12} color="var(--text-secondary)" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search pairs…"
            style={{ background: 'none', border: 'none', outline: 'none', fontSize: 12, color: 'var(--text-primary)', flex: 1 }} />
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', marginLeft: 'auto' }}>
          {loading ? 'Loading…' : `${enabled.length} / ${totalAvailable} selected`}
        </span>
        <button onClick={load} title="Reload" style={{ width: 30, height: 30, borderRadius: 7, border: '1px solid var(--border)', background: 'var(--card-hover)', cursor: 'pointer', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <RefreshCw size={12} />
        </button>
      </div>

      <div style={{ maxHeight: 360, overflowY: 'auto', padding: '6px 0' }}>
        {filtered.map(({ cat, pairs }) => (
          <div key={cat} style={{ padding: '10px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-secondary)' }}>
                {cat} <span style={{ opacity: 0.5 }}>{pairs.filter(p => isOn(p)).length}/{pairs.length}</span>
              </span>
              <button onClick={() => toggleCat(cat)}
                style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>
                {pairs.every(p => isOn(p)) ? 'Deselect all' : 'Select all'}
              </button>
            </div>
            {cat === SYNTH_CAT && (
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '-2px 0 8px' }}>
                Off unless you turn them on. They trade all week, weekends included.
              </p>
            )}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {pairs.map(pair => {
                const on = isOn(pair)
                return (
                  <button key={pair} onClick={() => toggle(pair)} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    padding: '4px 10px', borderRadius: 7, fontSize: 12, fontWeight: 500,
                    border: '1px solid', cursor: 'pointer', transition: 'all 0.1s',
                    borderColor: on ? 'var(--accent)' : 'var(--border)',
                    background: on ? 'var(--accent-bg)' : 'transparent',
                    color: on ? 'var(--accent-hover)' : 'var(--text-secondary)',
                  }}>
                    {on && <Check size={10} />}
                    {pair}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, background: 'var(--surface)', flexWrap: 'wrap' }}>
        <button onClick={save} disabled={saving || enabled.length === 0} style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '8px 18px', borderRadius: 8,
          fontSize: 13, fontWeight: 600, background: 'var(--accent)', color: 'white',
          border: 'none', cursor: 'pointer', opacity: saving || enabled.length === 0 ? 0.6 : 1,
          flexShrink: 0,
        }}>
          <Save size={13} /> {saving ? 'Saving…' : 'Save & Apply'}
        </button>
        {saveResult === 'ok' && (
          <span style={{ fontSize: 12, color: 'var(--bullish)', display: 'flex', alignItems: 'center', gap: 5, fontWeight: 500 }}>
            <CheckCircle size={13} /> Applied — takes effect on next job cycle
          </span>
        )}
        {saveResult === 'fail' && (
          <span style={{ fontSize: 12, color: 'var(--bearish)', display: 'flex', alignItems: 'center', gap: 5 }}>
            <XCircle size={13} /> Failed to save
          </span>
        )}
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>Alerts fire via TradingView webhook</span>
      </div>
    </div>
  )
}

function TelegramConnect() {
  const [connected, setConnected] = useState<boolean | null>(null)
  const [linkUrl, setLinkUrl] = useState<string | null>(null)
  const [waiting, setWaiting] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'ok' | 'fail' | null>(null)

  const loadStatus = async () => {
    try {
      const r = await apiFetch('/api/telegram/connection')
      const d = await r.json()
      setConnected(!!d.connected)
      setLinkUrl(d.link_url ?? null)
      return !!d.connected
    } catch { return false }
  }

  useEffect(() => { loadStatus() }, [])

  // While waiting for the user to press Start in Telegram, poll for the link.
  useEffect(() => {
    if (!waiting) return
    let tries = 0
    const id = setInterval(async () => {
      tries += 1
      const ok = await loadStatus()
      if (ok || tries >= 20) { setWaiting(false); clearInterval(id) }
    }, 3000)
    return () => clearInterval(id)
  }, [waiting])

  const handleConnect = () => {
    if (linkUrl) window.open(linkUrl, '_blank')
    setWaiting(true)
  }

  const handleDisconnect = async () => {
    await apiFetch('/api/telegram/disconnect', { method: 'POST' })
    setConnected(false)
    setTestResult(null)
  }

  const sendTest = async () => {
    setTesting(true); setTestResult(null)
    try {
      const res = await apiFetch('/api/telegram/test', { method: 'POST' })
      const d = await res.json().catch(() => ({}))
      setTestResult(d.ok ? 'ok' : 'fail')
    } catch { setTestResult('fail') }
    setTesting(false)
  }

  const btn: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 7, padding: '8px 18px', borderRadius: 8,
    fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer',
  }

  return (
    <div style={{ padding: '18px 20px' }}>
      {connected === null ? (
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading…</span>
      ) : connected ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--bullish)', fontWeight: 600 }}>
            <CheckCircle size={15} /> Telegram connected — your alerts arrive in your own chat.
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <button onClick={sendTest} disabled={testing} style={{ ...btn, background: 'var(--accent)', color: 'white', opacity: testing ? 0.6 : 1 }}>
              <Send size={13} /> {testing ? 'Sending…' : 'Send Test Message'}
            </button>
            <button onClick={handleDisconnect} style={{ ...btn, background: 'var(--card-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              Disconnect
            </button>
            {testResult === 'ok' && <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--bullish)', fontWeight: 500 }}><CheckCircle size={14} /> Delivered</span>}
            {testResult === 'fail' && <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--bearish)' }}><XCircle size={14} /> Failed</span>}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
            Connect your Telegram to receive your alerts. Tap the button below, then press
            <strong> Start</strong> in the chat that opens. You&apos;ll be linked automatically.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <button onClick={handleConnect} disabled={!linkUrl} style={{ ...btn, background: 'var(--accent)', color: 'white', opacity: linkUrl ? 1 : 0.6 }}>
              <Send size={13} /> Connect Telegram
            </button>
            <button onClick={loadStatus} style={{ ...btn, background: 'var(--card-hover)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              <RefreshCw size={13} /> Refresh
            </button>
            {waiting && <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Waiting for you to press Start in Telegram…</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const { user, refresh } = useAuth()
  const [name, setName] = useState('')
  const [nameSaved, setNameSaved] = useState(false)

  useEffect(() => {
    // Prefer the account name; fall back to localStorage
    setName(user?.name || loadUserName())
  }, [user])

  const saveName = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    saveUserName(trimmed)
    try {
      await apiFetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      })
      await refresh() // update the greeting immediately
    } catch { /* non-critical — localStorage already saved */ }
    setNameSaved(true)
    setTimeout(() => setNameSaved(false), 2000)
  }

  return (
    <>
      <TopBar title="Settings" subtitle="Instruments, account, and engine configuration" />
      <main className="page-padded" style={{ flex: 1, width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        <Section title="My Instruments" desc="Select which pairs you want to receive alerts for. Your choices are private and don't affect other users.">
          <InstrumentManager />
        </Section>

        <Section title="Profile" desc="Your display name shown on the Bias Board greeting.">
          <div style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', flex: '1 1 200px', minWidth: 0 }}>
                <User size={14} color="var(--text-secondary)" style={{ flexShrink: 0 }} />
                <input value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && saveName()}
                  placeholder="e.g. Alex"
                  style={{ background: 'none', border: 'none', outline: 'none', fontSize: 13, color: 'var(--text-primary)', flex: 1, minWidth: 0 }} />
              </div>
              <button onClick={saveName} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', flexShrink: 0 }}>
                <Save size={13} /> {nameSaved ? 'Saved ✓' : 'Save'}
              </button>
            </div>
          </div>
        </Section>

        <Section title="Telegram Alerts" desc="Connect your own Telegram so your alerts arrive in your personal chat.">
          <TelegramConnect />
        </Section>

        <Section title="Engine Configuration" desc="Read-only. Set via .env file.">
          <Row label="Tolerance band" value="5 pips" note="Reaction source tolerance for retest detection" />
          <Row label="Daily lookback" value="200 candles" note="Historical candles fetched on startup" />
          <Row label="H4 lookback" value="500 candles" note="Historical H4 candles fetched on startup" />
          <div style={{ display: 'flex', gap: 8, padding: '12px 20px', fontSize: 12, color: 'var(--text-secondary)', alignItems: 'flex-start' }}>
            <Info size={13} style={{ flexShrink: 0, marginTop: 1, color: 'var(--info)' }} />
            <span>Tolerance and lookback values require a restart to change.</span>
          </div>
        </Section>

      </main>
    </>
  )
}
