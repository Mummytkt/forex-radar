'use client'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight, Trophy, FlaskConical } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { INSTRUMENTS } from '@/components/TradeLogPage'
import { API_BASE } from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────
type Outcome = 'win' | 'loss' | 'be' | 'none'
interface EntryResult { outcome: Outcome; rr: number | null }
interface Trade {
  id: number
  trade_date: string
  instrument: string
  direction: 'buy' | 'sell'
  alert_type: string
  notes: string
  results: Record<string, EntryResult>
}

// Must match ENTRY_TYPES in api/entry_tests.py (the keys are stored)
const ENTRY_TYPES: { key: string; label: string }[] = [
  { key: 'direct_fvg', label: 'Direct entry on FVG' },
  { key: 'direct_engulfing', label: 'Direct entry on Engulfing' },
  { key: 'direct_h4_key', label: 'Direct entry on H4 fresh key level' },
  { key: 'h1_smc', label: '1H SMC confirmation' },
  { key: 'h1_engulfing', label: '1H Engulfing' },
  { key: 'h2_engulfing', label: '2H Engulfing' },
  { key: 'm5_cisd', label: '5M CISD' },
  { key: 'm5_smc', label: '5M SMC' },
  { key: 'm15_smc', label: '15M SMC' },
  { key: 'm15_cisd', label: '15M CISD' },
  { key: 'h4_3cr', label: '4H 3CR' },
  { key: 'h2_3cr', label: '2H 3CR' },
]
// The H4 alert each trade came from (same names as Alert Filters)
const ALERT_TYPES = [
  'Origin', 'Daily reaction + H4 breakout', 'H4 back in line', 'H4 breakout in line',
  'H4 Breaker', 'H4 OC reaction', 'H4 Engulfing', 'H4 FVG after breakout',
]
const OUTCOMES: { key: Outcome; label: string; color: string; bg: string }[] = [
  { key: 'win', label: 'Win', color: 'var(--bullish)', bg: 'var(--bullish-bg)' },
  { key: 'loss', label: 'Loss', color: 'var(--bearish)', bg: 'var(--bearish-bg)' },
  { key: 'be', label: 'BE', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  { key: 'none', label: 'No entry', color: 'var(--text-muted)', bg: 'var(--surface)' },
]
const RR_QUICK = [1, 2, 3, 4, 5, 6, 8, 10]

function hdrs(): HeadersInit {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' }
           : { 'Content-Type': 'application/json' }
}
function load(key: string, fallback: string): string {
  try { return localStorage.getItem(key) ?? fallback } catch { return fallback }
}
function save(key: string, v: string) {
  try { localStorage.setItem(key, v) } catch { /* private mode */ }
}
const today = () => new Date().toISOString().slice(0, 10)
const fmtR = (r: number) => `${r > 0 ? '+' : ''}${r.toFixed(2)}R`

// R a result made: win = its RR (unknown until set), loss = -1R, BE = 0
function rOf(r: EntryResult): number | null {
  if (r.outcome === 'win') return r.rr
  if (r.outcome === 'loss') return -1
  if (r.outcome === 'be') return 0
  return null
}

// ── Small UI pieces ───────────────────────────────────────────────────────────
function Chip({ on, color, bg, onClick, children }: { on: boolean; color: string; bg: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 10px', borderRadius: 7, fontSize: 12, fontWeight: 700, cursor: 'pointer',
      border: `1px solid ${on ? color : 'var(--border)'}`, background: on ? bg : 'transparent',
      color: on ? color : 'var(--text-muted)', whiteSpace: 'nowrap',
    }}>{children}</button>
  )
}
const selStyle: React.CSSProperties = {
  padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text-primary)', fontSize: 13,
}

// ── Scoreboard: every entry pattern compared across the trades ───────────────
function Scoreboard({ trades }: { trades: Trade[] }) {
  const rows = useMemo(() => ENTRY_TYPES.map(t => {
    let w = 0, l = 0, be = 0, none = 0, totalR = 0, rrSum = 0, rrN = 0, noRR = 0
    for (const tr of trades) {
      const r = tr.results[t.key]
      if (!r) continue
      if (r.outcome === 'win') { w++; if (r.rr != null) { rrSum += r.rr; rrN++ } else noRR++ }
      else if (r.outcome === 'loss') l++
      else if (r.outcome === 'be') be++
      else none++
      const v = rOf(r)
      if (v != null) totalR += v
    }
    const taken = w + l + be
    return { ...t, w, l, be, none, taken, noRR, totalR,
      winRate: taken ? (w / taken) * 100 : null,
      avgRR: rrN ? rrSum / rrN : null,
      expectancy: taken ? totalR / taken : null }
  }).sort((a, b) => (b.taken ? 1 : 0) - (a.taken ? 1 : 0) || b.totalR - a.totalR), [trades])

  const best = rows.find(r => r.taken > 0)
  const th: React.CSSProperties = { padding: '8px 10px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textAlign: 'right', whiteSpace: 'nowrap', textTransform: 'uppercase', letterSpacing: 0.3 }
  const td: React.CSSProperties = { padding: '8px 10px', fontSize: 13, color: 'var(--text-primary)', textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '14px 4px 6px', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 14px 10px', flexWrap: 'wrap' }}>
        <Trophy size={16} color="var(--accent)" />
        <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>Which entry holds up best</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {trades.length} trade{trades.length === 1 ? '' : 's'} · ranked by total R · loss = −1R, BE = 0
        </span>
        {best && <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: 'var(--bullish)' }}>Leader: {best.label}</span>}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th style={{ ...th, textAlign: 'left' }}>Entry</th>
              <th style={th}>Taken</th><th style={th}>Win</th><th style={th}>Loss</th><th style={th}>BE</th>
              <th style={th}>No entry</th><th style={th}>Win %</th><th style={th}>Avg RR (wins)</th>
              <th style={th}>Total R</th><th style={th}>R / trade</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.key} style={{ borderBottom: '1px solid var(--border)', opacity: r.taken || r.none ? 1 : 0.45 }}>
                <td style={{ ...td, textAlign: 'left', fontWeight: 600 }}>{r.label}</td>
                <td style={td}>{r.taken}</td>
                <td style={{ ...td, color: 'var(--bullish)' }}>{r.w}</td>
                <td style={{ ...td, color: 'var(--bearish)' }}>{r.l}</td>
                <td style={{ ...td, color: '#f59e0b' }}>{r.be}</td>
                <td style={{ ...td, color: 'var(--text-muted)' }}>{r.none}</td>
                <td style={{ ...td, fontWeight: 700 }}>{r.winRate == null ? '–' : `${r.winRate.toFixed(0)}%`}</td>
                <td style={td}>{r.avgRR == null ? '–' : r.avgRR.toFixed(2)}{r.noRR ? <span title="Wins with no RR set" style={{ color: 'var(--text-muted)' }}> ({r.noRR}?)</span> : null}</td>
                <td style={{ ...td, fontWeight: 800, color: r.totalR > 0 ? 'var(--bullish)' : r.totalR < 0 ? 'var(--bearish)' : 'var(--text-muted)' }}>{r.taken ? fmtR(r.totalR) : '–'}</td>
                <td style={td}>{r.expectancy == null ? '–' : fmtR(r.expectancy)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── One trade: tick each entry pattern's result ──────────────────────────────
function TradeCard({ trade, open, onToggle, onChange, onDelete }: {
  trade: Trade; open: boolean; onToggle: () => void
  onChange: (t: Trade) => void; onDelete: () => void
}) {
  const [customFor, setCustomFor] = useState<string | null>(null)
  const [customVal, setCustomVal] = useState('')
  const done = Object.keys(trade.results).length
  const tradeR = Object.values(trade.results).map(rOf).filter((v): v is number => v != null)

  const setResult = (key: string, r: EntryResult | null) => {
    const results = { ...trade.results }
    if (r) results[key] = r
    else delete results[key]
    onChange({ ...trade, results })
  }
  const tapOutcome = (key: string, o: Outcome) => {
    const cur = trade.results[key]
    if (cur?.outcome === o) setResult(key, null)   // tap again to clear
    else setResult(key, { outcome: o, rr: o === 'win' ? cur?.rr ?? null : null })
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, marginBottom: 10, overflow: 'hidden' }}>
      <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', cursor: 'pointer', flexWrap: 'wrap' }}>
        {open ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
        <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--text-primary)' }}>{trade.instrument}</span>
        <span style={{ fontSize: 11, fontWeight: 800, padding: '2px 8px', borderRadius: 6,
          color: trade.direction === 'buy' ? 'var(--bullish)' : 'var(--bearish)',
          background: trade.direction === 'buy' ? 'var(--bullish-bg)' : 'var(--bearish-bg)' }}>{trade.direction.toUpperCase()}</span>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{trade.trade_date}</span>
        {trade.alert_type && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>· {trade.alert_type}</span>}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          {done}/{ENTRY_TYPES.length} ticked
          {tradeR.length > 0 && <> · best <b style={{ color: 'var(--bullish)' }}>{fmtR(Math.max(...tradeR))}</b></>}
        </span>
      </div>
      {open && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '6px 14px 12px' }}>
          {ENTRY_TYPES.map(t => {
            const r = trade.results[t.key]
            return (
              <div key={t.key} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 0', borderBottom: '1px dashed var(--border)', flexWrap: 'wrap' }}>
                <span style={{ flex: '1 1 210px', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{t.label}</span>
                {OUTCOMES.map(o => (
                  <Chip key={o.key} on={r?.outcome === o.key} color={o.color} bg={o.bg} onClick={() => tapOutcome(t.key, o.key)}>{o.label}</Chip>
                ))}
                {r?.outcome === 'win' && (
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', flexBasis: '100%', paddingLeft: 4, marginTop: 2 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 2 }}>RR</span>
                    {RR_QUICK.map(n => (
                      <Chip key={n} on={r.rr === n} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => setResult(t.key, { outcome: 'win', rr: n })}>1:{n}</Chip>
                    ))}
                    {customFor === t.key ? (
                      <form onSubmit={e => { e.preventDefault(); const v = parseFloat(customVal); if (v > 0) setResult(t.key, { outcome: 'win', rr: v }); setCustomFor(null) }}>
                        <input autoFocus value={customVal} onChange={e => setCustomVal(e.target.value)} onBlur={() => setCustomFor(null)}
                          inputMode="decimal" placeholder="e.g. 2.7" style={{ ...selStyle, width: 80, padding: '4px 8px' }} />
                      </form>
                    ) : (
                      <Chip on={r.rr != null && !RR_QUICK.includes(r.rr)} color="var(--bullish)" bg="var(--bullish-bg)"
                        onClick={() => { setCustomFor(t.key); setCustomVal(r.rr != null ? String(r.rr) : '') }}>
                        {r.rr != null && !RR_QUICK.includes(r.rr) ? `1:${r.rr}` : 'Other…'}
                      </Chip>
                    )}
                  </div>
                )}
              </div>
            )
          })}
          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
            <input defaultValue={trade.notes} placeholder="Note (optional)" onBlur={e => e.target.value !== trade.notes && onChange({ ...trade, notes: e.target.value })}
              style={{ ...selStyle, flex: 1 }} />
            <button onClick={() => { if (confirm(`Delete this ${trade.instrument} trade?`)) onDelete() }}
              style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'transparent', color: 'var(--bearish)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              <Trash2 size={13} /> Delete
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function EntryTester({ tabs }: { tabs?: React.ReactNode }) {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [openId, setOpenId] = useState<number | null>(null)
  // New-trade bar: remembers the last pair / alert so the next one is one tap
  const [pair, setPair] = useState('')
  const [typing, setTyping] = useState(false)   // "Other…": a pair that isn't in the list
  const [date, setDate] = useState(today())
  const [dir, setDir] = useState<'buy' | 'sell'>('buy')
  const [alertType, setAlertType] = useState('')
  // Filters for the scoreboard and list
  const [fPair, setFPair] = useState('')
  const [fAlert, setFAlert] = useState('')
  const [fDir, setFDir] = useState('')

  useEffect(() => {
    setPair(load('mbp_et_pair', 'XAUUSD'))
    setAlertType(load('mbp_et_alert', 'Origin'))
    fetch(`${API_BASE}/api/entry-tests`, { headers: hdrs() })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: Trade[]) => { setTrades(d); if (d[0]) setOpenId(d[0].id) })
      .catch(() => setErr('Could not load your entry tests.'))
      .finally(() => setLoading(false))
  }, [])

  function body(t: Omit<Trade, 'id'>) { return JSON.stringify({
    trade_date: t.trade_date, instrument: t.instrument, direction: t.direction,
    alert_type: t.alert_type, notes: t.notes, results: t.results,
  }) }

  const addTrade = async () => {
    const p = pair.trim().toUpperCase().replace('/', '')
    if (!p) return
    save('mbp_et_pair', p)
    save('mbp_et_alert', alertType)
    const r = await fetch(`${API_BASE}/api/entry-tests`, {
      method: 'POST', headers: hdrs(),
      body: body({ trade_date: date, instrument: p, direction: dir, alert_type: alertType, notes: '', results: {} }),
    })
    if (!r.ok) { setErr('Could not add the trade.'); return }
    const t: Trade = await r.json()
    setTrades(prev => [t, ...prev])
    setOpenId(t.id)
    setErr('')
  }

  // Each tap saves straight away; the screen updates first so ticking stays fast.
  // Saves for one trade go one at a time, always sending its latest state.
  const pending = useRef<Record<number, Trade>>({})
  const busy = useRef<Record<number, boolean>>({})
  const flush = useCallback(async (id: number) => {
    if (busy.current[id]) return
    busy.current[id] = true
    while (pending.current[id]) {
      const t = pending.current[id]
      delete pending.current[id]
      try {
        const r = await fetch(`${API_BASE}/api/entry-tests/${id}`, { method: 'PUT', headers: hdrs(), body: body(t) })
        setErr(r.ok ? '' : 'A change did not save. Check your connection and tap it again.')
      } catch {
        setErr('A change did not save. Check your connection and tap it again.')
      }
    }
    busy.current[id] = false
  }, [])
  const update = useCallback((t: Trade) => {
    setTrades(prev => prev.map(x => x.id === t.id ? t : x))
    pending.current[t.id] = t
    flush(t.id)
  }, [flush])

  const remove = async (id: number) => {
    const r = await fetch(`${API_BASE}/api/entry-tests/${id}`, { method: 'DELETE', headers: hdrs() })
    if (r.ok) setTrades(prev => prev.filter(x => x.id !== id))
  }

  const shown = trades.filter(t => (!fPair || t.instrument === fPair) && (!fAlert || t.alert_type === fAlert) && (!fDir || t.direction === fDir))
  const pairs = Array.from(new Set(trades.map(t => t.instrument))).sort()
  // The remembered pair stays selectable even if it isn't in the standard list
  const pairOptions = Array.from(new Set([...(pair && !typing ? [pair] : []), ...INSTRUMENTS.map(i => i.replace('/', ''))]))

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <TopBar title="Entry Tester" />
      <main style={{ flex: 1, width: '100%', padding: '20px 24px', maxWidth: 1100 }}>
        {tabs}
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <FlaskConical size={20} color="var(--accent)" /> Entry Tester
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>
            Only you see this. For each trade, tap how every entry pattern did on that same trade. Each tap saves.
          </p>
        </div>

        {/* New trade */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 12, marginBottom: 20 }}>
          {typing ? (
            <input autoFocus value={pair} onChange={e => setPair(e.target.value)} onBlur={() => pair.trim() && setTyping(false)}
              placeholder="Type the pair" style={{ ...selStyle, width: 140 }} />
          ) : (
            <select value={pair} onChange={e => e.target.value === '__other' ? (setPair(''), setTyping(true)) : setPair(e.target.value)} style={selStyle}>
              {pairs.length > 0 && (
                <optgroup label="Tested already">{pairs.map(p => <option key={p} value={p}>{p}</option>)}</optgroup>
              )}
              <optgroup label="All pairs">
                {pairOptions.filter(p => !pairs.includes(p)).map(p => <option key={p} value={p}>{p}</option>)}
              </optgroup>
              <option value="__other">Other… (type it)</option>
            </select>
          )}
          <input type="date" value={date} onChange={e => setDate(e.target.value)} style={selStyle} />
          <Chip on={dir === 'buy'} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => setDir('buy')}>BUY</Chip>
          <Chip on={dir === 'sell'} color="var(--bearish)" bg="var(--bearish-bg)" onClick={() => setDir('sell')}>SELL</Chip>
          <select value={alertType} onChange={e => setAlertType(e.target.value)} style={selStyle}>
            {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <button onClick={addTrade} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontSize: 13, fontWeight: 700, marginLeft: 'auto' }}>
            <Plus size={14} /> Add trade
          </button>
        </div>

        {err && <div style={{ color: 'var(--bearish)', fontSize: 13, marginBottom: 12 }}>{err}</div>}

        {/* Filters */}
        {trades.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <select value={fPair} onChange={e => setFPair(e.target.value)} style={selStyle}>
              <option value="">All pairs</option>
              {pairs.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <select value={fAlert} onChange={e => setFAlert(e.target.value)} style={selStyle}>
              <option value="">All H4 alerts</option>
              {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={fDir} onChange={e => setFDir(e.target.value)} style={selStyle}>
              <option value="">Buys and sells</option>
              <option value="buy">Buys</option>
              <option value="sell">Sells</option>
            </select>
          </div>
        )}

        <Scoreboard trades={shown} />

        {loading ? <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>
          : shown.length === 0 ? <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No trades yet. Pick the pair, date, direction and H4 alert above, then Add trade.</p>
          : shown.map(t => (
            <TradeCard key={t.id} trade={t} open={openId === t.id}
              onToggle={() => setOpenId(openId === t.id ? null : t.id)}
              onChange={update} onDelete={() => remove(t.id)} />
          ))}
      </main>
    </div>
  )
}
