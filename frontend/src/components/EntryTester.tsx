'use client'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight, Trophy, FlaskConical, Camera, X } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { INSTRUMENTS } from '@/components/TradeLogPage'
import { API_BASE } from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────
type Outcome = 'win' | 'loss' | 'be' | 'none'
// takes: trades taken on this entry (a stop-out then a re-entry = 2); unset = 1
interface EntryResult { outcome: Outcome; rr: number | null; takes?: number }
interface Trade {
  id: number
  trade_date: string
  instrument: string
  direction: 'buy' | 'sell'
  alert_type: string
  notes: string
  exit_date?: string | null   // YYYY-MM-DD the trade closed
  results: Record<string, EntryResult>
  images: Record<string, number[]>   // {slot: image ids} — slot = a POI key or an entry key
}

// Must match POIS / MODELS in api/entry_tests.py (the keys are stored: "<model>_<poi>")
const POIS: { key: string; label: string }[] = [
  { key: 'fvg', label: 'H4 FVG' },
  { key: 'engulfing', label: 'H4 Engulfing' },
  { key: 'h4_key', label: 'H4 fresh key level' },
  { key: '3cr', label: '4H / 2H 3CR' },
]
const MODELS: { key: string; label: string }[] = [
  { key: 'direct', label: 'Direct entry' },
  { key: 'h1_cisd', label: '1H CISD' },
  { key: 'h1_engulfing', label: '1H Engulfing' },
  { key: 'h2_engulfing', label: '2H Engulfing' },
  { key: 'm5_cisd', label: '5M CISD' },
  { key: 'm15_cisd', label: '15M CISD' },
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
const BE_QUICK = [-0.5, -0.25, 0, 0.25, 0.5, 1]   // closed early: the R it was closed at

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
// Dates are chart dates (YYYY-MM-DD), read as calendar days, never shifted by timezone
const WDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
function dayOf(d?: string | null): Date | null {
  const m = d && /^(\d{4})-(\d{2})-(\d{2})$/.exec(d)
  return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : null
}
const weekday = (d?: string | null) => { const x = dayOf(d); return x ? WDAY[x.getUTCDay()] : '' }
// "Tue 28 Jan 2020"
const fmtDay = (d?: string | null) => {
  const x = dayOf(d)
  return x ? `${WDAY[x.getUTCDay()]} ${x.getUTCDate()} ${x.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })} ${x.getUTCFullYear()}` : ''
}
// How long it ran: calendar days, and the weekdays among them when a weekend sits in between
function heldFor(a?: string | null, b?: string | null): string {
  const x = dayOf(a), y = dayOf(b)
  if (!x || !y || y < x) return ''
  const days = Math.round((y.getTime() - x.getTime()) / 86400000)
  if (days === 0) return 'closed the same day'
  let wk = 0
  for (let t = x.getTime() + 86400000; t <= y.getTime(); t += 86400000) {
    const wd = new Date(t).getUTCDay()
    if (wd !== 0 && wd !== 6) wk++
  }
  return `held ${days} day${days === 1 ? '' : 's'}${wk !== days ? ` (${wk} trading day${wk === 1 ? '' : 's'})` : ''}`
}

// Trades grouped by year, then month (newest first), by the trade's entry date
function groupByPeriod(list: Trade[]) {
  const sorted = [...list].sort((a, b) => b.trade_date.localeCompare(a.trade_date) || b.id - a.id)
  const years: { year: string; trades: Trade[]; months: { key: string; trades: Trade[] }[] }[] = []
  for (const t of sorted) {
    const yk = t.trade_date.slice(0, 4), mk = t.trade_date.slice(0, 7)
    let y = years[years.length - 1]
    if (!y || y.year !== yk) { y = { year: yk, trades: [], months: [] }; years.push(y) }
    y.trades.push(t)
    let m = y.months[y.months.length - 1]
    if (!m || m.key !== mk) { m = { key: mk, trades: [] }; y.months.push(m) }
    m.trades.push(t)
  }
  return years
}
const monthName = (key: string) => {
  const d = dayOf(`${key}-01`)
  return d ? `${d.toLocaleString('en-GB', { month: 'long', timeZone: 'UTC' })} ${d.getUTCFullYear()}` : key
}

const today = () => new Date().toISOString().slice(0, 10)
const fmtR = (r: number) => `${r > 0 ? '+' : ''}${r.toFixed(2)}R`

// R a result made: win = its RR (unknown until set), loss = -1R, BE = 0
// Net R over every trade taken on the entry: each earlier stop-out is -1R, then
// the last one counts (win = its RR, loss = -1R, BE = 0)
function rOf(r: EntryResult): number | null {
  const before = Math.max((r.takes ?? 1) - 1, 0)
  if (r.outcome === 'win') return r.rr == null ? null : r.rr - before
  if (r.outcome === 'loss') return -1 - before
  if (r.outcome === 'be') return (r.rr ?? 0) - before   // closed early at r.rr (unset = exactly 0)
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
// The results table: for all trades (title "Which entry holds up best"), or one
// month / year of them (kind "month" / "year": a summary header above its trades)
function Scoreboard({ trades, title, kind, note }: { trades: Trade[]; title?: string; kind?: 'month' | 'year'; note?: string }) {
  const [poi, setPoi] = useState('')
  const [showAll, setShowAll] = useState(false)
  // Folded by default so the page stays calm; the overall table remembers the choice
  const [open, setOpenState] = useState(false)
  useEffect(() => { if (!kind) setOpenState(load('mbp_et_score_open', '0') === '1') }, [kind])
  const setOpen = (v: boolean) => { setOpenState(v); if (!kind) save('mbp_et_score_open', v ? '1' : '0') }
  // Period totals: buys / sells, and every entry's result added up (all POIs)
  const tot = useMemo(() => {
    let w = 0, l = 0, be = 0, r = 0
    for (const tr of trades)
      for (const t of ENTRY_TYPES) {
        const x = tr.results[t.key]
        if (!x) continue
        if (x.outcome === 'win') w++
        else if (x.outcome === 'loss') l++
        else if (x.outcome === 'be') be++
        const v = rOf(x)
        if (v != null) r += v
      }
    return { w, l, be, r, buys: trades.filter(t => t.direction === 'buy').length, sells: trades.filter(t => t.direction === 'sell').length }
  }, [trades])
  const all = useMemo(() => ENTRY_TYPES.filter(t => !poi || t.poi === poi).map(t => {
    let w = 0, l = 0, be = 0, none = 0, totalR = 0, rrSum = 0, rrN = 0, noRR = 0, trades_ = 0
    for (const tr of trades) {
      const r = tr.results[t.key]
      if (!r) continue
      if (r.outcome === 'win') { w++; if (r.rr != null) { rrSum += r.rr; rrN++ } else noRR++ }
      else if (r.outcome === 'loss') l++
      else if (r.outcome === 'be') be++
      else none++
      if (r.outcome !== 'none') trades_ += r.takes ?? 1
      const v = rOf(r)
      if (v != null) totalR += v
    }
    const taken = w + l + be
    return { ...t, w, l, be, none, taken, trades: trades_, noRR, totalR,
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
    <div style={{ background: kind ? 'var(--surface)' : 'var(--card)', border: `1px solid ${kind === 'year' ? 'var(--accent)' : 'var(--border)'}`, borderRadius: 12,
      padding: kind ? '10px 4px 4px' : '14px 4px 6px', marginBottom: kind ? 10 : 20, marginTop: kind === 'year' ? 6 : 0 }}>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: open ? '0 14px 10px' : '0 14px 6px', flexWrap: 'wrap', cursor: 'pointer' }}>
        {open ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
        <Trophy size={kind === 'month' ? 14 : 16} color="var(--accent)" />
        <span style={{ fontSize: kind === 'month' ? 14 : 15, fontWeight: 800, color: 'var(--text-primary)' }}>{title || 'Which entry holds up best'}</span>
        {note && <span style={{ fontSize: 11, fontWeight: 700, color: '#f59e0b' }}>{note}</span>}
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {trades.length} setup{trades.length === 1 ? '' : 's'} · <b style={{ color: 'var(--bullish)' }}>{tot.buys} buy{tot.buys === 1 ? '' : 's'}</b> · <b style={{ color: 'var(--bearish)' }}>{tot.sells} sell{tot.sells === 1 ? '' : 's'}</b>
          {' · '}entries: <b style={{ color: 'var(--bullish)' }}>{tot.w} W</b> · <b style={{ color: 'var(--bearish)' }}>{tot.l} L</b> · <b style={{ color: '#f59e0b' }}>{tot.be} BE</b>
          {' · '}<b style={{ color: tot.r > 0 ? 'var(--bullish)' : tot.r < 0 ? 'var(--bearish)' : 'var(--text-muted)' }}>{fmtR(tot.r)}</b>
          {!kind && ' · ranked by total R · each stop-out = −1R, BE = the R you closed at (0 if not set)'}
        </span>
        {best && <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: 'var(--bullish)' }}>{kind ? 'Best' : 'Leader'}: {best.label} {fmtR(best.totalR)}</span>}
      </div>
      {open && <>
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
              <th style={th} title="Setups where this entry was taken">Taken</th>
              <th style={th} title="Trades placed, re-entries included">Trades</th><th style={th}>Win</th><th style={th}>Loss</th><th style={th}>BE</th>
              <th style={th}>No entry</th><th style={th}>Win %</th><th style={th}>Avg RR (wins)</th>
              <th style={th}>Total R</th><th style={th}>R / trade</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.key} style={{ borderBottom: '1px solid var(--border)', opacity: r.taken || r.none ? 1 : 0.45 }}>
                <td style={{ ...td, textAlign: 'left', fontWeight: 600 }}>{r.label}</td>
                <td style={td}>{r.taken}</td>
                <td style={{ ...td, color: r.trades > r.taken ? 'var(--text-primary)' : 'var(--text-muted)' }}>{r.trades}</td>
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
      </>}
    </div>
  )
}

// ── Chart screenshots: several per POI, and per entry under a POI ──────────────
// Stored on the server (so they're there on every device). Click / drop / paste.
function authHdr(): HeadersInit {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return t ? { Authorization: `Bearer ${t}` } : {}
}

function Thumb({ id, label, onRemove }: { id: number; label: string; onRemove: () => void }) {
  const [url, setUrl] = useState<string | null>(null)
  const [big, setBig] = useState(false)
  useEffect(() => {
    let gone = false, made: string | null = null
    fetch(`${API_BASE}/api/entry-tests/images/${id}`, { headers: authHdr() })
      .then(r => r.ok ? r.blob() : Promise.reject())
      .then(b => { if (!gone) { made = URL.createObjectURL(b); setUrl(made) } })
      .catch(() => {})
    return () => { gone = true; if (made) URL.revokeObjectURL(made) }
  }, [id])
  return (
    <div style={{ position: 'relative', width: 150, height: 96, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface)' }}>
      {url
        ? <img src={url} alt={label} onClick={() => setBig(true)} style={{ width: '100%', height: '100%', objectFit: 'cover', cursor: 'zoom-in' }} />
        : <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: 8 }}>Loading…</div>}
      <button onClick={onRemove} aria-label="Remove image" title="Remove this image"
        style={{ position: 'absolute', top: 4, right: 4, background: 'rgba(0,0,0,0.65)', border: 'none', borderRadius: 6, padding: 3, color: 'white', cursor: 'pointer', display: 'flex' }}>
        <X size={13} />
      </button>
      {big && url && (
        <div onClick={() => setBig(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, cursor: 'zoom-out' }}>
          <img src={url} alt={label} style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 8 }} />
          <button aria-label="Close" style={{ position: 'absolute', top: 16, right: 16, background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 6, color: 'var(--text-primary)', cursor: 'pointer' }}><X size={18} /></button>
        </div>
      )}
    </div>
  )
}

function ImageStrip({ tradeId, slot, label, ids, onChange, compact }: {
  tradeId: number; slot: string; label: string; ids: number[]; onChange: (ids: number[]) => void; compact?: boolean
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)

  const upload = async (files: File[]) => {
    const imgs = files.filter(f => f.type.startsWith('image/'))
    if (!imgs.length) { setErr('That isn\'t an image file.'); return }
    setBusy(true); setErr('')
    let now = ids
    for (const f of imgs) {
      const fd = new FormData()
      fd.append('file', f)
      try {
        const r = await fetch(`${API_BASE}/api/entry-tests/${tradeId}/images/${slot}`, { method: 'POST', headers: authHdr(), body: fd })
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || '')
        now = [...now, (await r.json()).id]
        onChange(now)
      } catch (e) { setErr((e as Error).message || 'An image did not upload. Try again.'); break }
    }
    setBusy(false)
  }
  const remove = async (id: number) => {
    if (!confirm('Remove this image?')) return
    const r = await fetch(`${API_BASE}/api/entry-tests/images/${id}`, { method: 'DELETE', headers: authHdr() })
    if (r.ok) onChange(ids.filter(x => x !== id))
  }

  return (
    <div style={{ margin: compact ? '4px 0 2px' : '8px 0 6px', flexBasis: '100%' }}>
      <input ref={input} type="file" accept="image/*" multiple hidden onChange={e => { upload(Array.from(e.target.files || [])); e.target.value = '' }} />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'stretch' }}>
        {ids.map(id => <Thumb key={id} id={id} label={label} onRemove={() => remove(id)} />)}
        <div tabIndex={0} onClick={() => input.current?.click()}
          onPaste={e => upload(Array.from(e.clipboardData.files))}
          onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); upload(Array.from(e.dataTransfer.files)) }}
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', borderRadius: 8, border: '1px dashed var(--border)',
            color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer', outline: 'none', minHeight: ids.length ? 96 : undefined,
            maxWidth: ids.length ? 170 : undefined }}>
          <Camera size={15} style={{ flexShrink: 0 }} />
          {busy ? 'Uploading…' : ids.length
            ? <>Add another: click, drop, or click then paste</>
            : <>Add <b style={{ color: 'var(--text-secondary)' }}>{label}</b> images: click to choose (several at once is fine), drop files here, or click then paste (Ctrl+V)</>}
        </div>
      </div>
      {err && <div style={{ color: 'var(--bearish)', fontSize: 12, marginTop: 4 }}>{err}</div>}
    </div>
  )
}

// ── One trade: tick each entry pattern's result ──────────────────────────────
function TradeCard({ trade, open, onToggle, onChange, onImages, onDelete }: {
  trade: Trade; open: boolean; onToggle: () => void
  onChange: (t: Trade) => void; onImages: (images: Record<string, number[]>) => void; onDelete: () => void
}) {
  const [customFor, setCustomFor] = useState<string | null>(null)
  const [poi, setPoi] = useState(POIS[0].key)
  const [customVal, setCustomVal] = useState('')
  const [picsFor, setPicsFor] = useState<string | null>(null)   // entry row whose image strip is open
  const imgs = trade.images || {}
  const setSlot = (slot: string, ids: number[]) => {
    const images = { ...imgs }
    if (ids.length) images[slot] = ids
    else delete images[slot]
    onImages(images)
  }
  // Every picture under a POI: its own and its entries'
  const poiPics = (p: string) => Object.entries(imgs).filter(([k]) => k === p || k.endsWith(`_${p}`)).reduce((n, [, v]) => n + v.length, 0)
  const shownRes = ENTRY_TYPES.map(t => trade.results[t.key]).filter((r): r is EntryResult => !!r)   // hidden old keys not counted
  const done = shownRes.length
  const tradeR = shownRes.map(rOf).filter((v): v is number => v != null)

  const setResult = (key: string, r: EntryResult | null) => {
    const results = { ...trade.results }
    if (r) results[key] = r
    else delete results[key]
    onChange({ ...trade, results })
  }
  const tapOutcome = (key: string, o: Outcome) => {
    const cur = trade.results[key]
    if (cur?.outcome === o) setResult(key, null)   // tap again to clear
    else setResult(key, { outcome: o, rr: (o === 'win' && cur?.outcome === 'win') || (o === 'be' && cur?.outcome === 'be') ? cur?.rr ?? null : null, ...(o !== 'none' && cur?.takes ? { takes: cur.takes } : {}) })
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, marginBottom: 10, overflow: 'hidden' }}>
      <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', cursor: 'pointer', flexWrap: 'wrap' }}>
        {open ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
        <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--text-primary)' }}>{trade.instrument}</span>
        <span style={{ fontSize: 11, fontWeight: 800, padding: '2px 8px', borderRadius: 6,
          color: trade.direction === 'buy' ? 'var(--bullish)' : 'var(--bearish)',
          background: trade.direction === 'buy' ? 'var(--bullish-bg)' : 'var(--bearish-bg)' }}>{trade.direction.toUpperCase()}</span>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {fmtDay(trade.trade_date)}
          {trade.exit_date && <> → {fmtDay(trade.exit_date)} <span style={{ color: 'var(--text-muted)' }}>· {heldFor(trade.trade_date, trade.exit_date)}</span></>}
        </span>
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
                  {p.label}{n ? ` · ${n}` : ''}{poiPics(p.key) ? ` · 📷${poiPics(p.key)}` : ''}
                </Chip>
              )
            })}
          </div>
          <ImageStrip tradeId={trade.id} slot={poi} label={`${POIS.find(p => p.key === poi)?.label ?? poi} chart`}
            ids={imgs[poi] || []} onChange={ids => setSlot(poi, ids)} />
          {ENTRY_TYPES.filter(t => t.poi === poi).map(t => {
            const r = trade.results[t.key]
            return (
              <div key={t.key} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 0', borderBottom: '1px dashed var(--border)', flexWrap: 'wrap' }}>
                <span style={{ flex: '1 1 210px', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{t.model}</span>
                {OUTCOMES.map(o => (
                  <Chip key={o.key} on={r?.outcome === o.key} color={o.color} bg={o.bg} onClick={() => tapOutcome(t.key, o.key)}>{o.label}</Chip>
                ))}
                <Chip on={picsFor === t.key || !!imgs[t.key]?.length} color="var(--accent)" bg="var(--accent-bg)"
                  onClick={() => setPicsFor(picsFor === t.key ? null : t.key)}>
                  📷{imgs[t.key]?.length ? ` ${imgs[t.key].length}` : ''}
                </Chip>
                {(picsFor === t.key || !!imgs[t.key]?.length) && (
                  <ImageStrip compact tradeId={trade.id} slot={t.key} label={t.label} ids={imgs[t.key] || []}
                    onChange={ids => setSlot(t.key, ids)} />
                )}
                {r?.outcome === 'be' && (
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', flexBasis: '100%', paddingLeft: 4, marginTop: 2 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 2 }} title="Closed early, e.g. on a rejection: the R you closed at">Closed at</span>
                    {BE_QUICK.map(n => (
                      <Chip key={n} on={(r.rr ?? 0) === n} color="#f59e0b" bg="rgba(245,158,11,0.12)"
                        onClick={() => setResult(t.key, { ...r, rr: n === 0 ? null : n })}>{n > 0 ? `+${n}` : n}R</Chip>
                    ))}
                    <input type="number" step="0.1" min={-0.99} max={99} inputMode="decimal" placeholder="other" title="Type the R you closed at, e.g. 0.7 or -0.4"
                      defaultValue={r.rr != null && !BE_QUICK.includes(r.rr) ? r.rr : ''} key={`${t.key}-be-${r.rr ?? 0}`}
                      onBlur={e => { const v = parseFloat(e.target.value); if (!isNaN(v) && v > -1 && v < 100 && v !== (r.rr ?? 0)) setResult(t.key, { ...r, rr: v === 0 ? null : v }) }}
                      style={{ ...selStyle, width: 70, padding: '4px 8px' }} />
                  </div>
                )}
                {r?.outcome === 'win' && (
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', flexBasis: '100%', paddingLeft: 4, marginTop: 2 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 2 }}>RR</span>
                    {RR_QUICK.map(n => (
                      <Chip key={n} on={r.rr === n} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => setResult(t.key, { ...r, outcome: 'win', rr: n })}>1:{n}</Chip>
                    ))}
                    {customFor === t.key ? (
                      <form onSubmit={e => { e.preventDefault(); const v = parseFloat(customVal); if (v > 0) setResult(t.key, { ...r, outcome: 'win', rr: v }); setCustomFor(null) }}>
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
                {r && r.outcome !== 'none' && (
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', flexBasis: '100%', paddingLeft: 4, marginTop: 2 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 2 }} title="Stopped out and re-entered? Count every trade; the result above is the last one">Trades taken</span>
                    {[1, 2, 3, 4].map(n => (
                      <Chip key={n} on={(r.takes ?? 1) === n} color="var(--accent)" bg="var(--accent-bg)"
                        onClick={() => { const { takes: _t, ...rest } = r; setResult(t.key, n > 1 ? { ...rest, takes: n } : rest) }}>{n}</Chip>
                    ))}
                    <input type="number" min={1} max={50} inputMode="numeric" placeholder="5+" title="Type any number"
                      defaultValue={(r.takes ?? 1) > 4 ? r.takes : ''} key={`${t.key}-${r.takes ?? 1}`}
                      onBlur={e => { const n = parseInt(e.target.value, 10); if (n >= 1 && n <= 50 && n !== (r.takes ?? 1)) { const { takes: _t, ...rest } = r; setResult(t.key, n > 1 ? { ...rest, takes: n } : rest) } }}
                      style={{ ...selStyle, width: 58, padding: '4px 8px' }} />
                    {(r.takes ?? 1) > 1 && (() => { const v = rOf(r); return (
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', marginLeft: 4 }}>
                        {(r.takes ?? 1) - 1} stop-out{(r.takes ?? 1) > 2 ? 's' : ''} then {r.outcome === 'win' ? 'a win' : r.outcome === 'loss' ? 'a loss' : r.rr ? `a close at ${fmtR(r.rr)}` : 'BE'}
                        {v != null && <> = <b style={{ color: v > 0 ? 'var(--bullish)' : v < 0 ? 'var(--bearish)' : 'var(--text-muted)' }}>{fmtR(v)}</b> overall</>}
                      </span>) })()}
                  </div>
                )}
              </div>
            )
          })}
          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Edit the trade's details: pair, date, direction, H4 alert (each saves straight away) */}
            <span style={{ fontSize: 11, color: 'var(--text-muted)', flexBasis: '100%' }}>Trade details (edit any of them; changes save straight away)</span>
            <input defaultValue={trade.instrument} title="Pair (fix a spelling mistake here)"
              onInput={e => { e.currentTarget.value = cleanPair(e.currentTarget.value) }}
              onBlur={e => { const p = cleanPair(e.target.value); if (p && p !== trade.instrument) onChange({ ...trade, instrument: p }); else e.target.value = trade.instrument }}
              style={{ ...selStyle, width: 110 }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              Entry
              <input type="date" value={trade.trade_date} title="Entry date"
                onChange={e => e.target.value && onChange({ ...trade, trade_date: e.target.value })} style={selStyle} />
              <b style={{ color: 'var(--text-secondary)', minWidth: 28 }}>{weekday(trade.trade_date)}</b>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              Exit
              <input type="date" value={trade.exit_date || ''} min={trade.trade_date} title="Exit date (when the trade closed)"
                onChange={e => onChange({ ...trade, exit_date: e.target.value || null })} style={selStyle} />
              {trade.exit_date && <b style={{ color: 'var(--text-secondary)', minWidth: 28 }}>{weekday(trade.exit_date)}</b>}
              {trade.exit_date && <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{heldFor(trade.trade_date, trade.exit_date)}</span>}
            </label>
            <Chip on={trade.direction === 'buy'} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => trade.direction !== 'buy' && onChange({ ...trade, direction: 'buy' })}>BUY</Chip>
            <Chip on={trade.direction === 'sell'} color="var(--bearish)" bg="var(--bearish-bg)" onClick={() => trade.direction !== 'sell' && onChange({ ...trade, direction: 'sell' })}>SELL</Chip>
            <select value={trade.alert_type} title="H4 alert" onChange={e => onChange({ ...trade, alert_type: e.target.value })} style={selStyle}>
              {!ALERT_TYPES.includes(trade.alert_type) && <option value={trade.alert_type}>{trade.alert_type || '—'}</option>}
              {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <textarea defaultValue={trade.notes} placeholder="Notes (optional): saved when you click away" rows={3}
              onInput={e => { const t = e.currentTarget; t.style.height = 'auto'; t.style.height = `${t.scrollHeight + 2}px` }}
              ref={t => { if (t && !t.dataset.sized) { t.dataset.sized = '1'; t.style.height = 'auto'; t.style.height = `${Math.max(t.scrollHeight + 2, 72)}px` } }}
              onBlur={e => e.target.value !== trade.notes && onChange({ ...trade, notes: e.target.value })}
              style={{ ...selStyle, flexBasis: '100%', width: '100%', minHeight: 72, resize: 'vertical', lineHeight: 1.5, fontFamily: 'inherit' }} />
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
      .then((d: Trade[]) => setTrades(d))   // every trade starts folded; tap one to open it
      .catch(() => setErr('Could not load your entry tests.'))
      .finally(() => setLoading(false))
  }, [])

  function body(t: Omit<Trade, 'id'>) { return JSON.stringify({
    trade_date: t.trade_date, instrument: t.instrument, direction: t.direction,
    alert_type: t.alert_type, notes: t.notes, results: t.results, exit_date: t.exit_date || null,
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
  // The newest month you've logged is still running; earlier months are complete
  const latestMonth = trades.reduce((m, t) => (t.trade_date.slice(0, 7) > m ? t.trade_date.slice(0, 7) : m), '')
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
          : <div style={{ marginBottom: 20 }}>{groupByPeriod(shown).map(y => (
            <div key={y.year}>
              <Scoreboard kind="year" title={`${y.year}: year summary`} trades={y.trades}
                note={y.year === latestMonth.slice(0, 4) ? 'year so far' : undefined} />
              {y.months.map(m => (
                <div key={m.key} style={{ marginLeft: 10 }}>
                  <Scoreboard kind="month" title={monthName(m.key)} trades={m.trades}
                    note={m.key === latestMonth ? 'month so far' : undefined} />
                  {m.trades.map(t => (
                    <TradeCard key={t.id} trade={t} open={openId === t.id}
                      onToggle={() => setOpenId(openId === t.id ? null : t.id)}
                      onChange={update} onDelete={() => remove(t.id)}
                      onImages={images => setTrades(prev => prev.map(x => x.id === t.id ? { ...x, images } : x))} />
                  ))}
                </div>
              ))}
            </div>
          ))}</div>}

        {trades.length > 0 && <Scoreboard trades={shown} />}
      </main>
    </div>
  )
}
