'use client'
import { useState, useEffect } from 'react'
import { Send, CheckCircle, XCircle, User, Save, Info, Check, Search, RefreshCw } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { loadUserName, saveUserName } from '@/lib/preferences'

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
  'Metals': ['XAU/USD'],
  'Crypto': ['BTC/USD','ETH/USD','SOL/USD','BNB/USD','XRP/USD','ADA/USD','DOGE/USD','LTC/USD'],
}

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

  const load = async () => {
    setLoading(true)
    try {
      const r = await apiFetch('/api/config/instruments')
      const data = await r.json()
      setEnabled(data.instruments ?? [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const isOn = (p: string) => enabled.includes(p)

  const toggle = (p: string) =>
    setEnabled(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p])

  const toggleCat = (cat: string) => {
    const pairs = ALL_INSTRUMENTS[cat]
    const allOn = pairs.every(p => isOn(p))
    if (allOn) setEnabled(prev => prev.filter(p => !pairs.includes(p)))
    else setEnabled(prev => [...new Set([...prev, ...pairs])])
  }

  const save = async () => {
    if (enabled.length === 0) return
    setSaving(true)
    setSaveResult(null)
    try {
      const r = await apiFetch('/api/config/instruments', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruments: enabled }),
      })
      setSaveResult(r.ok ? 'ok' : 'fail')
    } catch { setSaveResult('fail') }
    setSaving(false)
    setTimeout(() => setSaveResult(null), 4000)
  }

  const totalAvailable = Object.values(ALL_INSTRUMENTS).flat().length
  const filtered = Object.entries(ALL_INSTRUMENTS)
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

      <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, background: 'var(--surface)' }}>
        <button onClick={save} disabled={saving || enabled.length === 0} style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '8px 18px', borderRadius: 8,
          fontSize: 13, fontWeight: 600, background: 'var(--accent)', color: 'white',
          border: 'none', cursor: 'pointer', opacity: saving || enabled.length === 0 ? 0.6 : 1,
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

export default function SettingsPage() {
  const [name, setName] = useState('')
  const [nameSaved, setNameSaved] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'ok' | 'fail' | null>(null)

  useEffect(() => { setName(loadUserName()) }, [])

  const saveName = () => {
    saveUserName(name.trim())
    setNameSaved(true)
    setTimeout(() => setNameSaved(false), 2000)
  }

  const sendTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiFetch('/api/telegram/test', { method: 'POST' })
      setTestResult(res.ok ? 'ok' : 'fail')
    } catch { setTestResult('fail') }
    setTesting(false)
  }

  return (
    <>
      <TopBar title="Settings" subtitle="Instruments, account, and engine configuration" />
      <main style={{ flex: 1, padding: '24px', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 20 }}>

        <Section title="Monitored Instruments" desc="Choose which pairs the engine analyses. Changes apply on the next TradingView webhook — no restart needed.">
          <InstrumentManager />
        </Section>

        <Section title="Profile" desc="Your display name shown on the Overview greeting.">
          <div style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', flex: 1 }}>
                <User size={14} color="var(--text-secondary)" />
                <input value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && saveName()}
                  placeholder="e.g. Alex"
                  style={{ background: 'none', border: 'none', outline: 'none', fontSize: 13, color: 'var(--text-primary)', flex: 1 }} />
              </div>
              <button onClick={saveName} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer' }}>
                <Save size={13} /> {nameSaved ? 'Saved ✓' : 'Save'}
              </button>
            </div>
          </div>
        </Section>

        <Section title="Telegram Alerts" desc="Alerts are sent via your bot when all 4 conditions confirm.">
          <Row label="Bot token" value="configured ✓" note="Set via TELEGRAM_BOT_TOKEN env variable" />
          <Row label="Chat ID" value="configured ✓" note="Set via TELEGRAM_CHAT_ID env variable" />
          <Row label="Delivery" value="enabled" note="Alerts fire automatically on H4 confirmation" />
          <div style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button onClick={sendTest} disabled={testing} style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '8px 18px', borderRadius: 8,
                fontSize: 13, fontWeight: 500, background: 'var(--accent)', color: 'white',
                border: 'none', cursor: 'pointer', opacity: testing ? 0.6 : 1,
              }}>
                <Send size={13} /> {testing ? 'Sending…' : 'Send Test Message'}
              </button>
              {testResult === 'ok' && <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--bullish)', fontWeight: 500 }}><CheckCircle size={14} /> Delivered</span>}
              {testResult === 'fail' && <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--bearish)' }}><XCircle size={14} /> Failed — check credentials</span>}
            </div>
          </div>
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
