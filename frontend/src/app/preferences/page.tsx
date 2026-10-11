'use client'
import { useState, useEffect } from 'react'
import { Search, Check } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { loadPrefs, savePrefs, type UserPreferences } from '@/lib/preferences'
import { API_BASE } from '@/lib/api'

function authHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {}
  const t = localStorage.getItem('mbp_token')
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

const ALL_PAIRS: Record<string, string[]> = {
  'Majors': ['EUR/USD','GBP/USD','USD/JPY','USD/CHF','USD/CAD','AUD/USD','NZD/USD'],
  'EUR Crosses': ['EUR/JPY','EUR/GBP','EUR/AUD','EUR/CAD','EUR/NZD','EUR/CHF'],
  'GBP Crosses': ['GBP/JPY','GBP/AUD','GBP/CAD','GBP/NZD','GBP/CHF'],
  'Commodity Crosses': ['AUD/JPY','AUD/CAD','AUD/NZD','AUD/CHF','NZD/JPY','NZD/CAD','NZD/CHF','CAD/JPY','CAD/CHF','CHF/JPY'],
  'Metals': ['XAU/USD'],
  'Crypto': ['BTC/USD','ETH/USD','SOL/USD','BNB/USD','XRP/USD','ADA/USD','DOGE/USD','LTC/USD'],
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <div className="toggle-track">
        <div className="toggle-thumb" />
      </div>
    </label>
  )
}

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<UserPreferences | null>(null)
  const [search, setSearch] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const local = loadPrefs()
    setPrefs(local)
    // Override alertExternal/alertInternal from backend (they control Telegram delivery)
    fetch(`${API_BASE}/api/preferences`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d && typeof d.alertExternal === 'boolean') {
          setPrefs(prev => prev ? { ...prev, alertExternal: d.alertExternal, alertInternal: d.alertInternal } : prev)
        }
      })
      .catch(() => {})
  }, [])

  const save = async () => {
    if (!prefs) return
    // Save display-only prefs to localStorage
    savePrefs(prefs)
    // Save alert-type delivery prefs to backend
    try {
      await fetch(`${API_BASE}/api/preferences`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({ alertExternal: prefs.alertExternal, alertInternal: prefs.alertInternal }),
      })
    } catch { /* non-critical — localStorage already saved */ }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const isAllEnabled = !prefs || prefs.enabledPairs.length === 0
  const isPairEnabled = (pair: string) => isAllEnabled || prefs!.enabledPairs.includes(pair)

  const togglePair = (pair: string) => {
    if (!prefs) return
    const allPairs = Object.values(ALL_PAIRS).flat()
    let next: string[]
    if (isAllEnabled) {
      next = allPairs.filter(p => p !== pair)
    } else if (prefs.enabledPairs.includes(pair)) {
      next = prefs.enabledPairs.filter(p => p !== pair)
      if (next.length === 0) next = []
    } else {
      next = [...prefs.enabledPairs, pair]
      if (next.length === allPairs.length) next = []
    }
    setPrefs({ ...prefs, enabledPairs: next })
  }

  const toggleCategory = (cat: string) => {
    if (!prefs) return
    const catPairs = ALL_PAIRS[cat]
    const allEnabled = catPairs.every(p => isPairEnabled(p))
    const allPairs = Object.values(ALL_PAIRS).flat()
    let current = isAllEnabled ? [...allPairs] : [...prefs.enabledPairs]
    let next: string[]
    if (allEnabled) {
      next = current.filter(p => !catPairs.includes(p))
    } else {
      const toAdd = catPairs.filter(p => !current.includes(p))
      next = [...current, ...toAdd]
      if (next.length === allPairs.length) next = []
    }
    setPrefs({ ...prefs, enabledPairs: next })
  }

  if (!prefs) return null

  const filteredCategories = Object.entries(ALL_PAIRS).map(([cat, pairs]) => ({
    cat,
    pairs: search ? pairs.filter(p => p.toLowerCase().includes(search.toLowerCase())) : pairs,
  })).filter(({ pairs }) => pairs.length > 0)

  return (
    <>
      <TopBar title="Preferences" subtitle="Filter what you see in History — does not affect what the engine monitors" />
      <main style={{ flex: 1, padding: '24px', maxWidth: 720, display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Explanation banner */}
        <div style={{
          display: 'flex', gap: 12, padding: '13px 16px', borderRadius: 10,
          background: 'var(--card)', border: '1px solid var(--border)', fontSize: 12,
          color: 'var(--text-secondary)', lineHeight: 1.7, alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>ℹ️</span>
          <span>
            <strong style={{ color: 'var(--text-primary)' }}>Preferences only affect your History view.</strong>
            {' '}Unchecked pairs are not removed from monitoring — the engine still watches them and your Telegram still receives their alerts.
            To add or remove pairs from the engine entirely, go to{' '}
            <a href="/settings" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>Settings → Instruments</a>.
          </span>
        </div>

        {/* Alert types */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Telegram Delivery</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Which confirmation types reach your Telegram. Saved to the engine — takes effect immediately.</p>
          </div>
          <div style={{ padding: '4px 0' }}>
            {[
              { key: 'alertExternal' as const, label: 'External breakouts', desc: 'Bias confirmed by a close beyond the pre-tap structure. The standard alert.' },
              { key: 'alertInternal' as const, label: 'Internal breakouts', desc: 'Earlier confirmation from the first internal break after a rejection.' },
            ].map(({ key, label, desc }) => (
              <div key={key} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '14px 20px', borderBottom: '1px solid var(--border)',
              }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{label}</p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>{desc}</p>
                </div>
                <Toggle checked={prefs[key]} onChange={v => setPrefs({ ...prefs, [key]: v })} />
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px' }}>
              <div>
                <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>Direction filter</p>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>Receive buy alerts, sell alerts, or both.</p>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['ALL','BULLISH','BEARISH'] as const).map(d => (
                  <button key={d} onClick={() => setPrefs({ ...prefs, direction: d })}
                    style={{
                      padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 500,
                      border: '1px solid', cursor: 'pointer',
                      borderColor: prefs.direction === d ? 'var(--accent)' : 'var(--border)',
                      background: prefs.direction === d ? 'var(--accent)' : 'transparent',
                      color: prefs.direction === d ? 'white' : 'var(--text-secondary)',
                    }}>
                    {d === 'ALL' ? 'Both' : d === 'BULLISH' ? '↑ Buy' : '↓ Sell'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Pairs */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div>
                <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Pairs</h2>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                  {isAllEnabled ? 'All pairs selected (default).' : `${prefs.enabledPairs.length} pairs selected.`}
                </p>
              </div>
              {!isAllEnabled && (
                <button onClick={() => setPrefs({ ...prefs, enabledPairs: [] })}
                  style={{ fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>
                  Select all
                </button>
              )}
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '7px 12px',
            }}>
              <Search size={13} color="var(--text-secondary)" />
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search pairs, e.g. EURUSD or XAUUSD"
                style={{
                  background: 'none', border: 'none', outline: 'none',
                  fontSize: 13, color: 'var(--text-primary)', flex: 1,
                }}
              />
            </div>
          </div>

          <div style={{ maxHeight: 420, overflow: 'auto' }}>
            {filteredCategories.map(({ cat, pairs }) => {
              const catEnabled = pairs.every(p => isPairEnabled(p))
              const catCount = pairs.filter(p => isPairEnabled(p)).length
              return (
                <div key={cat} style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                      {cat} <span style={{ opacity: 0.6 }}>{catCount} of {pairs.length}</span>
                    </span>
                    <button onClick={() => toggleCategory(cat)}
                      style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>
                      {catEnabled ? 'Clear' : 'Select all'}
                    </button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {pairs.map(pair => {
                      const enabled = isPairEnabled(pair)
                      return (
                        <button key={pair} onClick={() => togglePair(pair)}
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: 5,
                            padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                            border: '1px solid', cursor: 'pointer',
                            borderColor: enabled ? 'var(--accent)' : 'var(--border)',
                            background: enabled ? 'var(--accent-bg)' : 'transparent',
                            color: enabled ? 'var(--accent-hover)' : 'var(--text-secondary)',
                            transition: 'all 0.1s',
                          }}>
                          {enabled && <Check size={10} />}
                          {pair}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Save */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={save}
            style={{
              padding: '9px 24px', borderRadius: 9, fontSize: 13, fontWeight: 600,
              background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(99,102,241,0.35)',
              transition: 'opacity 0.1s',
            }}>
            Save changes
          </button>
          {saved && (
            <span style={{ fontSize: 12, color: 'var(--bullish)', display: 'flex', alignItems: 'center', gap: 5, fontWeight: 500 }}>
              <Check size={13} /> Saved
            </span>
          )}
        </div>
      </main>
    </>
  )
}
