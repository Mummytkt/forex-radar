'use client'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight, Trophy, FlaskConical, Camera, X } from 'lucide-react'
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
  images: Record<string, number>   // {poi: image id}
}

// Must match POIS / MODELS in api/entry_tests.py (the keys are stored: "<model>_<poi>")
const POIS: { key: string; label: string }[] = [
  { key: 'fvg', label: 'H4 FVG' },
  { key: 'engulfing', label: 'H4 Engulfing' },
  { key: 'h4_key', label: 'H4 fresh key level' },
]
const MODELS: { key: string; label: string }[] = [
  { key: 'direct', label: 'Direct entry' },
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
const ENTRY_TYPES: { key: string; label: string; model: string; poi: string }[] = POIS.flatMap(p =>
  MODELS.map(m => ({ key: `${m.key}_${p.key}`, label: `${m.label} on ${p.label}`, model: m.label, poi: p.key })))
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
// Pairs are stored like EURUSD: capitals, no slash or spaces
const cleanPair = (s: string) => s.toUpperCase().replace(/[^A-Z0-9_.]/g, '')
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
  const [poi, setPoi] = useState('')
  const [showAll, setShowAll] = useState(false)
  const all = useMemo(() => ENTRY_TYPES.filter(t => !poi || t.poi === poi).map(t => {
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
  }).sort((a, b) => (b.taken ? 1 : 0) - (a.taken ? 1 : 0) || b.totalR - a.totalR), [trades, poi])

  const tested = all.filter(r => r.taken || r.none)
  const rows = showAll || tested.length === 0 ? all : tested
  const best = all.find(r => r.taken > 0)
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
      <div style={{ display: 'flex', gap: 6, padding: '0 14px 10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <Chip on={!poi} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi('')}>All POIs</Chip>
        {POIS.map(p => <Chip key={p.key} on={poi === p.key} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi(p.key)}>{p.label}</Chip>)}
        {tested.length > 0 && tested.length < all.length && (
          <button onClick={() => setShowAll(v => !v)} style={{ marginLeft: 'auto', border: 'none', background: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
            {showAll ? 'Hide the untested ones' : `Show all ${all.length} (incl. untested)`}
          </button>
        )}
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

// ── Chart screenshot for one POI of a trade ──────────────────────────────────
// Stored on the server (so it's there on every device). Click / drop / paste.
function PoiImage({ tradeId, poi, poiLabel, imageId, onSet }: {
  tradeId: number; poi: string; poiLabel: string; imageId?: number; onSet: (id: number | null) => void
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [big, setBig] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!imageId) { setUrl(null); return }
    let gone = false, made: string | null = null
    const t = localStorage.getItem('mbp_token')
    fetch(`${API_BASE}/api/entry-tests/images/${imageId}`, { headers: t ? { Authorization: `Bearer ${t}` } : {} })
      .then(r => r.ok ? r.blob() : Promise.reject())
      .then(b => { if (!gone) { made = URL.createObjectURL(b); setUrl(made) } })
      .catch(() => !gone && setErr('Could not load the image.'))
    return () => { gone = true; if (made) URL.revokeObjectURL(made) }
  }, [imageId])

  const upload = async (file: File | null | undefined) => {
    if (!file || !file.type.startsWith('image/')) { setErr('That isn\'t an image file.'); return }
    setBusy(true); setErr('')
    const fd = new FormData()
    fd.append('file', file)
    const t = localStorage.getItem('mbp_token')
    try {
      const r = await fetch(`${API_BASE}/api/entry-tests/${tradeId}/images/${poi}`, {
        method: 'POST', headers: t ? { Authorization: `Bearer ${t}` } : {}, body: fd })
      if (!r.ok) throw new Error()
      onSet((await r.json()).id)
    } catch { setErr('The image did not upload. Try again.') }
    setBusy(false)
  }
  const remove = async () => {
    if (!confirm(`Remove the ${poiLabel} image?`)) return
    const t = localStorage.getItem('mbp_token')
    const r = await fetch(`${API_BASE}/api/entry-tests/${tradeId}/images/${poi}`, {
      method: 'DELETE', headers: t ? { Authorization: `Bearer ${t}` } : {} })
    if (r.ok) onSet(null)
  }

  return (
    <div style={{ margin: '8px 0 4px' }}>
      <input ref={input} type="file" accept="image/*" hidden onChange={e => { upload(e.target.files?.[0]); e.target.value = '' }} />
      {url ? (
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <img src={url} alt={`${poiLabel} chart`} onClick={() => setBig(true)}
            style={{ maxWidth: 360, width: '100%', borderRadius: 8, border: '1px solid var(--border)', cursor: 'zoom-in' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button onClick={() => input.current?.click()} disabled={busy} style={{ ...selStyle, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              {busy ? 'Uploading…' : 'Replace image'}
            </button>
            <button onClick={remove} style={{ ...selStyle, cursor: 'pointer', fontSize: 12, fontWeight: 600, color: 'var(--bearish)' }}>Remove</button>
          </div>
        </div>
      ) : (
        <div tabIndex={0} onClick={() => input.current?.click()}
          onPaste={e => upload(Array.from(e.clipboardData.files)[0])}
          onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); upload(e.dataTransfer.files[0]) }}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 14px', borderRadius: 8, border: '1px dashed var(--border)',
            color: 'var(--text-muted)', fontSize: 13, cursor: 'pointer', outline: 'none' }}>
          <Camera size={16} />
          {busy ? 'Uploading…' : <>Add the <b style={{ color: 'var(--text-secondary)' }}>{poiLabel}</b> chart image: click to choose, drop a file here, or click then paste (Ctrl+V)</>}
        </div>
      )}
      {err && <div style={{ color: 'var(--bearish)', fontSize: 12, marginTop: 4 }}>{err}</div>}
      {big && url && (
        <div onClick={() => setBig(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, cursor: 'zoom-out' }}>
          <img src={url} alt={`${poiLabel} chart`} style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 8 }} />
          <button aria-label="Close" style={{ position: 'absolute', top: 16, right: 16, background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 6, color: 'var(--text-primary)', cursor: 'pointer' }}><X size={18} /></button>
        </div>
      )}
    </div>
  )
}

// ── One trade: tick each entry pattern's result ──────────────────────────────
function TradeCard({ trade, open, onToggle, onChange, onImages, onDelete }: {
  trade: Trade; open: boolean; onToggle: () => void
  onChange: (t: Trade) => void; onImages: (images: Record<string, number>) => void; onDelete: () => void
}) {
  const [customFor, setCustomFor] = useState<string | null>(null)
  const [poi, setPoi] = useState(POIS[0].key)
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
          {done} ticked
          {tradeR.length > 0 && <> · best <b style={{ color: 'var(--bullish)' }}>{fmtR(Math.max(...tradeR))}</b></>}
        </span>
      </div>
      {open && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '10px 14px 12px' }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
            {POIS.map(p => {
              const n = ENTRY_TYPES.filter(t => t.poi === p.key && trade.results[t.key]).length
              return (
                <Chip key={p.key} on={poi === p.key} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi(p.key)}>
                  {p.label}{n ? ` · ${n}` : ''}{trade.images?.[p.key] ? ' · 📷' : ''}
                </Chip>
              )
            })}
          </div>
          <PoiImage tradeId={trade.id} poi={poi} poiLabel={POIS.find(p => p.key === poi)?.label ?? poi}
            imageId={trade.images?.[poi]}
            onSet={id => {
              const images = { ...(trade.images || {}) }
              if (id) images[poi] = id
              else delete images[poi]
              onImages(images)
            }} />
          {ENTRY_TYPES.filter(t => t.poi === poi).map(t => {
            const r = trade.results[t.key]
            return (
              <div key={t.key} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 0', borderBottom: '1px dashed var(--border)', flexWrap: 'wrap' }}>
                <span style={{ flex: '1 1 210px', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{t.model}</span>
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
          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Fix a misspelt pair on this trade */}
            <input defaultValue={trade.instrument} title="Pair (fix a spelling mistake here)"
              onInput={e => { e.currentTarget.value = cleanPair(e.currentTarget.value) }}
              onBlur={e => { const p = cleanPair(e.target.value); if (p && p !== trade.instrument) onChange({ ...trade, instrument: p }); else e.target.value = trade.instrument }}
              style={{ ...selStyle, width: 110 }} />
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
    setPair(cleanPair(load('mbp_et_pair', 'XAUUSD')) || 'XAUUSD')
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
    const p = cleanPair(pair)
    if (!p) return
    save('mbp_et_pair', p)
    save('mbp_et_alert', alertType)
    const r = await fetch(`${API_BASE}/api/entry-tests`, {
      method: 'POST', headers: hdrs(),
      body: body({ trade_date: date, instrument: p, direction: dir, alert_type: alertType, notes: '', results: {}, images: {} }),
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
  const stdPairs = INSTRUMENTS.map(i => i.replace('/', ''))
  const pairOptions = Array.from(new Set([...(pair && !typing ? [pair] : []), ...stdPairs]))
  // A pair typed under "Other…" that has no trades yet can be removed again
  const customPair = !typing && !!pair && !stdPairs.includes(pair) && !pairs.includes(pair)
  const removePair = () => { setPair('XAUUSD'); save('mbp_et_pair', 'XAUUSD') }

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
            <input autoFocus value={pair} onChange={e => setPair(cleanPair(e.target.value))} onBlur={() => pair.trim() && setTyping(false)}
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
          {customPair && (
            <button onClick={removePair} title={`Remove ${pair} from the list`}
              style={{ padding: '6px 9px', borderRadius: 7, border: '1px solid var(--border)', background: 'transparent', color: 'var(--bearish)', cursor: 'pointer', fontSize: 12, fontWeight: 700 }}>
              ✕ Remove {pair}
            </button>
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

        {/* Your trades first (this is where you tick), the results summary under them */}
        {loading ? <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>
          : trades.length === 0 ? (
            <div style={{ background: 'var(--card)', border: '1px dashed var(--border)', borderRadius: 12, padding: '18px 20px', marginBottom: 20, color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7 }}>
              <div style={{ fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6 }}>How to log a trade</div>
              <div><b>1.</b> In the bar above, pick the <b>pair</b>, the <b>date</b>, <b>BUY</b> or <b>SELL</b>, and the <b>H4 alert</b> it came from.</div>
              <div><b>2.</b> Tap <b>Add trade</b>. The trade opens right here.</div>
              <div><b>3.</b> Pick the POI tab (<b>H4 FVG</b>, <b>H4 Engulfing</b> or <b>H4 fresh key level</b>), then tap <b>Win</b>, <b>Loss</b>, <b>BE</b> or <b>No entry</b> on each entry model. On a win, tap the RR.</div>
              <div><b>4.</b> Every tap saves. The results table fills in by itself.</div>
            </div>
          )
          : shown.length === 0 ? <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>No trades match these filters.</p>
          : <div style={{ marginBottom: 20 }}>{shown.map(t => (
            <TradeCard key={t.id} trade={t} open={openId === t.id}
              onToggle={() => setOpenId(openId === t.id ? null : t.id)}
              onChange={update} onDelete={() => remove(t.id)}
              onImages={images => setTrades(prev => prev.map(x => x.id === t.id ? { ...x, images } : x))} />
          ))}</div>}

        {trades.length > 0 && <Scoreboard trades={shown} />}
      </main>
    </div>
  )
}
