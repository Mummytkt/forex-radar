'use client'
import { useState, useEffect, useMemo, useCallback, useRef, createContext, useContext } from 'react'
import { createPortal } from 'react-dom'
import { Plus, Trash2, ChevronDown, ChevronRight, Trophy, FlaskConical, Camera, X, Eye, Pencil, Check, Download, Printer } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { INSTRUMENTS } from '@/components/TradeLogPage'
import { API_BASE } from '@/lib/api'
import DateInput from '@/components/DateInput'
import { useAuth } from '@/lib/auth'
import { buildStory } from '@/lib/diaryStory'
import { bookHtml, BOOK_WAIT, type BookChapter, type BookInput, type BookPage, type BookPicture } from '@/lib/diaryBook'
import { downloadBookPdf } from '@/lib/diaryBookPdf'
import { numberTrades, tradesWord, entriesIn, streaks, NO_NUM, type TradeNum } from '@/lib/tradeNumbers'
import { CHECK_ITEMS, CHECK_RATIOS, EMPTY_CHECKLIST, checklistText, type Checklist } from '@/lib/checklist'

// A journal limited to one POI (the live Engulfing / Fresh Key Levels Journals): ''
// = every POI (the backtest Entry Tester). Read by the scoreboards and trade cards.
const OnlyPoi = createContext('')

// ── Types ─────────────────────────────────────────────────────────────────────
type Outcome = 'win' | 'loss' | 'be' | 'none'
// takes: trades taken on this entry (a stop-out then a re-entry = 2); unset = 1
// exit: when this entry's trade closed ("YYYY-MM-DDTHH:MM"); each entry model can close at a different time
interface EntryResult { outcome: Outcome; rr: number | null; takes?: number; exit?: string }
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
  checklist?: Checklist   // the Checklist journal's tick boxes (empty on the other journals)
}

// Must match POIS / MODELS in api/entry_tests.py (the keys are stored: "<model>_<poi>")
const NEW_MODELS: { key: string; label: string }[] = [
  { key: 'lc1', label: 'LC 1' },
  { key: 'lc2', label: 'LC 2' },
]
// Taken off on 2026-11-06: a row shows only on a trade that already has a result or picture on it
const RETIRED_MODELS: { key: string; label: string; retired: true }[] = [
  { key: 'oc1h', label: '15M OC (old)', retired: true },
  { key: 'cisd1h', label: '1H CISD (old)', retired: true },
  { key: 'pcl1h', label: '1H PCL (old)', retired: true },
]
// The older journals keep their own list, so their trades still read as they were logged
const OLD_MODELS: { key: string; label: string }[] = [
  { key: 'direct', label: 'Direct entry' },
  { key: 'h1_cisd', label: '1H PCL' },   // keys kept from when these were called CISD
  { key: 'm5_cisd', label: '5M SMC' },
  { key: 'm15_cisd', label: '15M SMC' },
]
// The Checklist journal's rows: the entries tried on every trade, to see which suits the POIs best (2026-11-09).
// Must match CHK_MODELS in api/entry_tests.py (keys are stored)
const CHK_MODELS: { key: string; label: string }[] = [
  { key: 'e_cisd1h_inst', label: '1hr CISD, Instant entry' },
  { key: 'e_cisd1h_lim', label: '1hr CISD, Limit entry' },
  { key: 'e_eg1h_inst', label: '1hr EG, Instant entry' },
  { key: 'e_eg1h_lim', label: '1hr EG, Limit entry' },
  { key: 'e_octgd1h_inst', label: '1hr OCTGD, Instant entry' },
  { key: 'e_octgd1h_lim', label: '1hr OCTGD, Limit entry' },
  { key: 'e_pcl1h_lim', label: '1hr PCL, Limit entry' },
  { key: 'e_pcl1h_inst', label: '1hr PCL, Instant entry' },
  { key: 'e_cisd15_inst', label: '15mins CISD, Instant entry' },
  { key: 'e_cisd15_lim', label: '15mins CISD, Limit entry' },
  { key: 'e_smc5_lim', label: '5mins SMC, Limit entry' },
  { key: 'e_smc5_inst', label: '5mins SMC, Instant entry' },
]
// Its earlier rows: LC 1 / LC 2, then five entry types (2026-11-08). They show only on a trade already ticked there
const CHK_OLD: { key: string; label: string; retired: true }[] = [
  ...NEW_MODELS.map(m => ({ ...m, label: `${m.label} (old)`, retired: true as const })),
  { key: 'e_direct', label: 'Direct entry (old)', retired: true as const },
  { key: 'e_cisd15', label: '15M CISD (old)', retired: true as const },
  { key: 'e_cisd1h', label: '1H CISD (old)', retired: true as const },
  { key: 'e_octgd1h', label: 'H1 OCTGD (old)', retired: true as const },
  { key: 'e_smc5', label: '5M SMC (old)', retired: true as const },
  { key: 'e_cisd5_inst', label: '5mins CISD, Instant entry (old)', retired: true as const },   // taken off 2026-11-09
  { key: 'e_smc15_bqm', label: '15mins SMC, Breaker / QM entry (old)', retired: true as const },   // taken off 2026-11-09
  { key: 'e_eg1h_smc5', label: '1hr EG, 5mins SMC entry (old)', retired: true as const },   // taken off 2026-11-09
]
const MODELS = [...NEW_MODELS, ...CHK_MODELS, ...CHK_OLD.slice(NEW_MODELS.length), ...RETIRED_MODELS, ...OLD_MODELS]
const POIS: { key: string; label: string; old?: boolean }[] = [
  { key: 'scl', label: 'H1 entry' },   // keys kept from their first names (SCL, high/low liquidity before POI)
  { key: 'chk', label: 'Checklist' },   // 2026-11-08: LC 1 / LC 2 like the H1 entry, plus the checklist
  { key: 'hl_liq', label: 'M15 entry' },
  { key: 'engulfing', label: 'H4 Engulfing', old: true },
  { key: 'h4_key', label: 'H4 fresh key level', old: true },
]
const ENTRY_TYPES: { key: string; label: string; model: string; mkey: string; poi: string; poiLabel: string; retired: boolean }[] = POIS.flatMap(p =>
  (p.old ? OLD_MODELS : p.key === 'chk' ? [...CHK_MODELS, ...CHK_OLD] : [...NEW_MODELS, ...RETIRED_MODELS]).map(m => ({
    key: `${m.key}_${p.key}`, label: `${m.label} on ${p.label}`, model: m.label, mkey: m.key, poi: p.key, poiLabel: p.label,
    retired: 'retired' in m })))
// The H4 alert picker is hidden for now (2026-11-06: the owner writes it in the notes). true brings all of it back:
// the add bar, the filter, the trade's details and its header. Alerts on trades already saved stay stored.
const SHOW_H4_ALERT = false
// The H4 alert each trade came from (same names as Alert Filters)
const ALERT_TYPES = [
  'Daily breakout', 'H4 continuation after the Daily breakout', 'H4 pullback confirmed', 'H4 continuation after the pullback',
  'H4 pullback: back in alignment', 'H4 continuation in alignment', 'Inside the H4 range: H4 against the Daily',
]
const OUTCOMES: { key: Outcome; label: string; color: string; bg: string }[] = [
  { key: 'win', label: 'Win', color: 'var(--bullish)', bg: 'var(--bullish-bg)' },
  { key: 'loss', label: 'Loss', color: 'var(--loss)', bg: 'var(--loss-bg)' },
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

// Every date box here: selStyle's look on the site's one date field
function DateText({ width, ...p }: { value: string | null | undefined; onChange: (v: string) => void; withTime?: boolean; min?: string; placeholder?: string; width?: number }) {
  return <DateInput {...p} style={{ ...selStyle, padding: p.withTime ? '4px 8px' : selStyle.padding, ...(width ? { width } : {}) }} />
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

function Streak({ s }: { s: ReturnType<typeof streaks> }) {
  if (!s.nowO) return <span style={{ color: 'var(--text-muted)' }}>–</span>
  return (
    <span title="Now = the run still going (newest results). Longest wins / losses in a row. BE and no entry don't break a run.">
      <b style={{ color: s.nowO === 'win' ? SOFT.up : SOFT.loss }}>{s.now}{s.nowO === 'win' ? 'W' : 'L'} now</b>
      <span style={{ color: 'var(--text-muted)' }}> · best </span><b style={{ color: SOFT.up }}>{s.bestW}W</b>
      <span style={{ color: 'var(--text-muted)' }}> · worst </span><b style={{ color: SOFT.loss }}>{s.worstL}L</b>
    </span>
  )
}

// ── Small UI pieces ───────────────────────────────────────────────────────────
function Chip({ on, color, bg, onClick, children }: { on: boolean; color: string; bg: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
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
// Muted colours for the summaries (full-strength ones were too loud next to each other)
const SOFT = {
  up: 'color-mix(in srgb, var(--bullish) 72%, transparent)', dn: 'color-mix(in srgb, var(--bearish) 72%, transparent)',
  be: 'rgba(245,158,11,0.72)', ac: 'color-mix(in srgb, var(--accent) 75%, var(--text-secondary))',
  row: 'rgba(127,127,127,0.07)', upBg: 'color-mix(in srgb, var(--bullish) 9%, transparent)',
  dnBg: 'color-mix(in srgb, var(--bearish) 9%, transparent)', beBg: 'rgba(245,158,11,0.08)',
  // A loss is a plain, full-strength red, never softened and not the pink a SELL uses
  loss: 'var(--loss)', lossBg: 'var(--loss-bg)',
}

// The results table: for all trades (title "Which entry holds up best"), or one
// month / year of them (kind "month" / "year": a summary header above its trades)
// children: shown inside the box under the table when it's open (a month's trades)
function Scoreboard({ trades, title, kind, note, children, openWith }: {
  trades: Trade[]; title?: string; kind?: 'month' | 'year'; note?: string; children?: React.ReactNode; openWith?: boolean
}) {
  const only = useContext(OnlyPoi)
  const [poi, setPoi] = useState(only)
  const [showAll, setShowAll] = useState(false)
  // Grouped by entry pattern (its POIs under it) by default, or by POI. A one-POI
  // journal is always one group: its confirmation models ranked best first.
  const [byPick, setByState] = useState<'entry' | 'poi'>('entry')
  const by = only ? 'poi' : byPick
  useEffect(() => { setByState(load('mbp_et_group', 'entry') === 'poi' ? 'poi' : 'entry') }, [])
  const setBy = (v: 'entry' | 'poi') => { setByState(v); save('mbp_et_group', v) }
  const chrono = useMemo(() => [...trades].sort((a, b) => a.trade_date.localeCompare(b.trade_date) || a.id - b.id), [trades])
  // Folded by default so the page stays calm; the overall table remembers the choice
  const [open, setOpenState] = useState(false)
  const [report, setReport] = useState(false)   // a month's report table, folded inside the month
  useEffect(() => { if (!kind) setOpenState(load('mbp_et_score_open', '0') === '1') }, [kind])
  useEffect(() => { if (openWith) setOpenState(true) }, [openWith])   // e.g. the month of a trade just added
  const setOpen = (v: boolean) => { setOpenState(v); if (!kind) save('mbp_et_score_open', v ? '1' : '0') }
  // Period totals: buys / sells, and every entry's result added up (all POIs)
  const tot = useMemo(() => {
    let w = 0, l = 0, be = 0, r = 0
    for (const tr of trades)
      for (const t of ENTRY_TYPES) {
        const x = tr.results[t.key]
        if (!x || (only && t.poi !== only)) continue
        const e = entriesIn(x)
        w += e.w; l += e.l; be += e.be
        const v = rOf(x)
        if (v != null) r += v
      }
    return { w, l, be, r, buys: trades.filter(t => t.direction === 'buy').length, sells: trades.filter(t => t.direction === 'sell').length }
  }, [trades, only])
  const all = useMemo(() => ENTRY_TYPES.filter(t => !poi || t.poi === poi).map(t => {
    let w = 0, l = 0, be = 0, none = 0, totalR = 0, rrSum = 0, rrN = 0, noRR = 0, trades_ = 0, setups = 0
    // Each trade's result for this entry, oldest first: the run of wins and losses
    const seq: { o: Outcome; r: number | null; takes?: number; tip: string }[] = []
    for (const tr of chrono) {
      const x = tr.results[t.key]
      if (x && x.outcome !== 'none')
        seq.push({ o: x.outcome, r: rOf(x), takes: x.takes, tip: `${fmtDay(tr.trade_date)} · ${tr.instrument} ${tr.direction.toUpperCase()}` +
          `${(x.takes ?? 1) > 1 ? ` · ${x.takes} trades` : ''}${x.exit ? ` · closed ${fmtDay(x.exit.slice(0, 10))} ${x.exit.slice(11, 16)} (${heldFor(tr.trade_date, x.exit.slice(0, 10))})` : ''}` })
    }
    for (const tr of trades) {
      const r = tr.results[t.key]
      if (!r) continue
      if (r.outcome === 'win') { if (r.rr != null) { rrSum += r.rr; rrN++ } else noRR++ }
      if (r.outcome === 'none') none++
      else setups++
      const e = entriesIn(r)
      w += e.w; l += e.l; be += e.be
      trades_ += e.w + e.l + e.be
      const v = rOf(r)
      if (v != null) totalR += v
    }
    return { ...t, w, l, be, none, taken: setups, trades: trades_, noRR, totalR, seq, streak: streaks(seq),
      winRate: trades_ ? (w / trades_) * 100 : null,
      avgRR: rrN ? rrSum / rrN : null,
      expectancy: trades_ ? totalR / trades_ : null }
  }).filter(r => !r.retired || r.taken || r.none).sort((a, b) => (b.taken ? 1 : 0) - (a.taken ? 1 : 0) || b.totalR - a.totalR), [trades, poi, chrono])

  const tested = all.filter(r => r.taken || r.none)
  const rows = showAll || tested.length === 0 ? all : tested
  // Best entry pattern = its results on ALL POIs added up (not one POI's result)
  const best = useMemo(() => {
    let top: { label: string; r: number; w: number; n: number } | null = null
    for (const m of MODELS) {
      let r = 0, w = 0, n = 0
      for (const tr of trades)
        for (const p of POIS.filter(x => !only || x.key === only)) {
          const x = tr.results[`${m.key}_${p.key}`]
          if (!x || x.outcome === 'none') continue
          const e = entriesIn(x)
          n += e.w + e.l + e.be
          w += e.w
          const v = rOf(x)
          if (v != null) r += v
        }
      if (n && (!top || r > top.r)) top = { label: m.label, r, w, n }
    }
    return top
  }, [trades, only])
  const th: React.CSSProperties = { padding: '8px 10px', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textAlign: 'right', whiteSpace: 'nowrap', textTransform: 'uppercase', letterSpacing: 0.3 }
  const td: React.CSSProperties = { padding: '8px 10px', fontSize: 13, color: 'var(--text-primary)', textAlign: 'right', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }
  return (
    <div data-diary-card="" style={{ background: kind ? 'var(--surface)' : 'var(--card)', border: `1px solid ${kind === 'year' ? 'var(--accent)' : 'var(--border)'}`, borderRadius: 12,
      padding: kind ? '10px 4px 4px' : '14px 4px 6px', marginBottom: kind ? 10 : 20, marginTop: kind === 'year' ? 6 : 0 }}>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: open ? '0 14px 10px' : '0 14px 6px', flexWrap: 'wrap', cursor: 'pointer' }}>
        {open ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
        <Trophy size={kind === 'month' ? 14 : 16} color="var(--accent)" />
        <span className="diary-sum" style={{ fontSize: kind === 'month' ? 14 : 15, fontWeight: 800, color: 'var(--text-primary)' }}>{title || 'Which entry holds up best'}</span>
        {note && <span className="diary-sum" style={{ fontSize: 11, fontWeight: 700, color: SOFT.be }}>{note}</span>}
        {/* The Checklist journal: each trade is one setup taken, its entry rows are samples of the same trade, so the
            line counts setups only; the entries are compared in the report */}
        {only === 'chk' ? (
        <span className="diary-sum" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          <b style={{ color: 'var(--text-secondary)' }}>{trades.length} setup{trades.length === 1 ? '' : 's'} taken</b> · <b style={{ color: SOFT.up }}>{tot.buys} buy{tot.buys === 1 ? '' : 's'}</b> · <b style={{ color: SOFT.dn }}>{tot.sells} sell{tot.sells === 1 ? '' : 's'}</b>
          {!kind && ' · each entry is tried on every setup; the table compares them, best first'}
        </span>
        ) : (
        <span className="diary-sum" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {trades.length} setup{trades.length === 1 ? '' : 's'} · {tot.w + tot.l + tot.be} {tot.w + tot.l + tot.be === 1 ? 'entry' : 'entries'} · <b style={{ color: SOFT.up }}>{tot.buys} buy{tot.buys === 1 ? '' : 's'}</b> · <b style={{ color: SOFT.dn }}>{tot.sells} sell{tot.sells === 1 ? '' : 's'}</b>
          {' · '}<b style={{ color: SOFT.up }}>{tot.w} W</b> · <b style={{ color: SOFT.loss }}>{tot.l} L</b> · <b style={{ color: SOFT.be }}>{tot.be} BE</b>
          {' · '}<b style={{ color: tot.r > 0 ? SOFT.up : tot.r < 0 ? SOFT.loss : 'var(--text-muted)' }}>{fmtR(tot.r)}</b>
          {!kind && ' · ranked by total R · each stop-out = −1R, BE = the R you closed at (0 if not set)'}
        </span>
        )}
        {best && <span className="diary-sum" style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: best.r < 0 ? SOFT.loss : SOFT.up }}>{kind ? 'Best entry' : 'Leading entry'}: {best.label} · {fmtR(best.r)} · {Math.round((best.w / best.n) * 100)}% wins{only ? '' : ' (all POIs)'}</span>}
      </div>
      {open && children && (
        <div onClick={() => setReport(!report)} style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0 14px 8px', padding: '7px 10px',
          borderRadius: 8, border: '1px solid var(--border)', cursor: 'pointer', fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>
          {report ? <ChevronDown size={14} /> : <ChevronRight size={14} />} {title} report: results by entry pattern
        </div>
      )}
      {open && (report || !children) && <>
      <div style={{ display: 'flex', gap: 6, padding: '0 14px 10px', flexWrap: 'wrap', alignItems: 'center' }}>
        {only ? <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Confirmation models, best first</span> : <>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Group by</span>
        <Chip on={by === 'entry'} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setBy('entry')}>Entry pattern</Chip>
        <Chip on={by === 'poi'} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setBy('poi')}>POI</Chip>
        <span style={{ width: 1, height: 18, background: 'var(--border)', margin: '0 4px' }} />
        <Chip on={!poi} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi('')}>All POIs</Chip>
        {POIS.map(p => <Chip key={p.key} on={poi === p.key} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi(p.key)}>{p.label}</Chip>)}
        </>}
        {tested.length > 0 && tested.length < all.length && (
          <button onClick={() => setShowAll(v => !v)} style={{ marginLeft: 'auto', border: 'none', background: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
            {showAll ? 'Hide the untested ones' : `Show all ${all.length} (incl. untested)`}
          </button>
        )}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 980 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th style={{ ...th, textAlign: 'left' }}>Entry</th>
              <th style={th} title="Setups where this entry was taken">Taken</th>
              <th style={th} title="Trades placed, re-entries included">Trades</th><th style={th}>Win</th><th style={th}>Loss</th><th style={th}>BE</th>
              <th style={th}>No entry</th><th style={th}>Win %</th><th style={th}>Avg RR (wins)</th>
              <th style={th}>Total R</th><th style={th}>R / trade</th>
              <th style={th} title="Wins / losses in a row, counting every entry: the run going now, the longest win run, the longest loss run. BE and no entry don't break a run.">Streak</th>
              <th style={{ ...th, textAlign: 'left' }} title="Each setup's result for this entry, oldest first. Hover a badge for the date and pair.">Results (oldest → newest)</th>
            </tr>
          </thead>
          <tbody>
            {/* Grouped by POI (each POI's entries together, best first), with that POI's totals */}
            {(by === 'entry'
              ? MODELS.map(m => ({ key: m.key, label: m.label, grp: rows.filter(r => r.mkey === m.key) }))
                  .sort((a, b) => b.grp.reduce((n, r) => n + r.totalR, 0) - a.grp.reduce((n, r) => n + r.totalR, 0))
              : POIS.filter(x => !poi || x.key === poi).map(x => ({ key: x.key, label: x.label, grp: rows.filter(r => r.poi === x.key) }))
            ).map(p => {
              const grp = p.grp
              if (!grp.length) return null
              const g = grp.reduce((a, r) => ({ taken: a.taken + r.taken, trades: a.trades + r.trades, w: a.w + r.w, l: a.l + r.l,
                be: a.be + r.be, none: a.none + r.none, totalR: a.totalR + r.totalR }), { taken: 0, trades: 0, w: 0, l: 0, be: 0, none: 0, totalR: 0 })
              const gTaken = g.w + g.l + g.be
              return [
                <tr key={`grp-${p.key}`} style={{ background: SOFT.row, borderBottom: '1px solid var(--border)' }}>
                  <td style={{ ...td, textAlign: 'left', fontWeight: 800, color: SOFT.ac }}>{p.label}</td>
                  <td style={{ ...td, fontWeight: 700 }}>{g.taken}</td>
                  <td style={{ ...td, fontWeight: 700 }}>{g.trades}</td>
                  <td style={{ ...td, fontWeight: 700, color: SOFT.up }}>{g.w}</td>
                  <td style={{ ...td, fontWeight: 700, color: SOFT.loss }}>{g.l}</td>
                  <td style={{ ...td, fontWeight: 700, color: SOFT.be }}>{g.be}</td>
                  <td style={{ ...td, color: 'var(--text-muted)' }}>{g.none}</td>
                  <td style={{ ...td, fontWeight: 800 }}>{gTaken ? `${((g.w / gTaken) * 100).toFixed(0)}%` : '–'}</td>
                  <td style={td}></td>
                  <td style={{ ...td, fontWeight: 800, color: g.totalR > 0 ? SOFT.up : g.totalR < 0 ? SOFT.loss : 'var(--text-muted)' }}>{gTaken ? fmtR(g.totalR) : '–'}</td>
                  <td style={g.totalR < 0 ? { ...td, color: SOFT.loss } : td}>{gTaken ? fmtR(g.totalR / gTaken) : '–'}</td>
                  <td style={td}></td>
                  <td style={td}></td>
                </tr>,
                ...grp.map(r => (
              <tr key={r.key} style={{ borderBottom: '1px solid var(--border)', opacity: r.taken || r.none ? 1 : 0.45 }}>
                <td style={{ ...td, textAlign: 'left', fontWeight: 600, paddingLeft: 24 }} title={r.label}>{by === 'entry' ? r.poiLabel : r.model}</td>
                <td style={td}>{r.taken}</td>
                <td style={{ ...td, color: r.trades > r.taken ? 'var(--text-primary)' : 'var(--text-muted)' }}>{r.trades}</td>
                <td style={{ ...td, color: SOFT.up }}>{r.w}</td>
                <td style={{ ...td, color: SOFT.loss }}>{r.l}</td>
                <td style={{ ...td, color: SOFT.be }}>{r.be}</td>
                <td style={{ ...td, color: 'var(--text-muted)' }}>{r.none}</td>
                <td style={{ ...td, fontWeight: 700 }}>{r.winRate == null ? '–' : `${r.winRate.toFixed(0)}%`}</td>
                <td style={td}>{r.avgRR == null ? '–' : r.avgRR.toFixed(2)}{r.noRR ? <span title="Wins with no RR set" style={{ color: 'var(--text-muted)' }}> ({r.noRR}?)</span> : null}</td>
                <td style={{ ...td, fontWeight: 800, color: r.totalR > 0 ? SOFT.up : r.totalR < 0 ? SOFT.loss : 'var(--text-muted)' }}>{r.taken ? fmtR(r.totalR) : '–'}</td>
                <td style={r.expectancy != null && r.expectancy < 0 ? { ...td, color: SOFT.loss } : td}>{r.expectancy == null ? '–' : fmtR(r.expectancy)}</td>
                <td style={td}><Streak s={r.streak} /></td>
                <td style={{ ...td, textAlign: 'left', whiteSpace: 'normal' }}>
                  <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', maxWidth: 380 }}>
                    {r.seq.map((x, i) => (
                      <span key={i} title={`${x.tip}${x.r != null ? ` · ${fmtR(x.r)}` : ''}`}
                        style={{ fontSize: 10.5, fontWeight: 800, padding: '2px 5px', borderRadius: 5,
                          color: x.o === 'win' ? SOFT.up : x.o === 'loss' ? SOFT.loss : SOFT.be,
                          background: x.o === 'win' ? SOFT.upBg : x.o === 'loss' ? SOFT.lossBg : SOFT.beBg }}>
                        {x.o === 'win' ? 'W' : x.o === 'loss' ? 'L' : 'BE'}{x.r != null && x.o !== 'loss' ? ` ${x.r > 0 ? '+' : ''}${+x.r.toFixed(2)}` : x.r != null && x.r !== -1 ? ` ${+x.r.toFixed(2)}` : ''}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
                )),
              ]
            })}
          </tbody>
        </table>
      </div>
      </>}
      {open && children && <div style={{ padding: '4px 10px 4px' }}>{children}</div>}
    </div>
  )
}

// ── Chart screenshots: several per POI, and per entry under a POI ──────────────
// Stored on the server (so they're there on every device). Click / drop / paste.
function authHdr(): HeadersInit {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return t ? { Authorization: `Bearer ${t}` } : {}
}

function Thumb({ id, label, onRemove }: { id: number; label: string; onRemove?: () => void }) {
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
  useEffect(() => {   // Esc closes the big picture
    if (!big) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setBig(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [big])
  return (
    <div style={{ position: 'relative', width: 150, height: 96, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--surface)' }}>
      {url
        ? <img src={url} alt={label} onClick={() => setBig(true)} style={{ width: '100%', height: '100%', objectFit: 'cover', cursor: 'zoom-in' }} />
        : <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: 8 }}>Loading…</div>}
      {onRemove && <button onClick={onRemove} aria-label="Remove image" title="Remove this image"
        style={{ position: 'absolute', top: 4, right: 4, background: 'rgba(0,0,0,0.65)', border: 'none', borderRadius: 6, padding: 3, color: 'white', cursor: 'pointer', display: 'flex' }}>
        <X size={13} />
      </button>}
      {/* On the page body, so no card or animation around the picture can trap or clip it */}
      {big && url && createPortal(
        <div onClick={e => { e.stopPropagation(); setBig(false) }} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.88)', zIndex: 10000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, cursor: 'zoom-out' }}>
          <img src={url} alt={label} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 8 }} />
          <button aria-label="Close" style={{ position: 'absolute', top: 16, right: 16, background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 6, color: 'var(--text-primary)', cursor: 'pointer', display: 'flex' }}><X size={18} /></button>
        </div>,
        document.body,
      )}
    </div>
  )
}

// pickTick: each time it goes up, the device's picture picker opens straight away (the 📷 button on a row). pickAt is
// when the button was tapped: a strip that appears later (e.g. the trade opened in Edit again) must not open the picker.
// onCancel: the picker was closed with nothing chosen and the row has no pictures, so the strip can close again
function ImageStrip({ tradeId, slot, label, ids, onChange, compact, pickTick = 0, pickAt = 0, onCancel }: {
  tradeId: number; slot: string; label: string; ids: number[]; onChange: (ids: number[]) => void; compact?: boolean
  pickTick?: number; pickAt?: number; onCancel?: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { if (pickTick && Date.now() - pickAt < 1000) input.current?.click() }, [pickTick])   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const el = input.current
    if (!el || !onCancel) return
    const cancelled = () => { if (!ids.length) onCancel() }
    el.addEventListener('cancel', cancelled)
    return () => el.removeEventListener('cancel', cancelled)
  }, [ids.length, onCancel])

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

// ── The Checklist journal ────────────────────────────────────────────────────
function TickBox({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} aria-pressed={on} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 11px', borderRadius: 8, cursor: 'pointer',
      border: `1px solid ${on ? 'var(--accent)' : 'var(--border)'}`, background: on ? 'var(--accent-bg)' : 'transparent',
      color: on ? 'var(--text-primary)' : 'var(--text-secondary)', fontSize: 13, fontWeight: 600, textAlign: 'left' }}>
      <span style={{ width: 17, height: 17, borderRadius: 4, flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        border: `2px solid ${on ? 'var(--accent)' : 'var(--text-muted)'}`, background: on ? 'var(--accent)' : 'transparent' }}>
        {on && <Check size={12} color="white" strokeWidth={3.5} />}
      </span>
      {label}
    </button>
  )
}
// Each tap saves, like the rest of the trade
function ChecklistBox({ value, onChange }: { value: Checklist; onChange: (c: Checklist) => void }) {
  const items = value.items || []
  const flip = (k: string) => onChange({ ...value, items: items.includes(k) ? items.filter(x => x !== k) : [...items, k] })
  return (
    <div style={{ padding: '6px 0 10px', borderBottom: '1px dashed var(--border)' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 6 }}>Checklist</div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {CHECK_ITEMS.map(i => <TickBox key={i.key} on={items.includes(i.key)} label={i.label} onClick={() => flip(i.key)} />)}
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginTop: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginRight: 4 }}>Highest Ratio Done</span>
        {CHECK_RATIOS.map(r => <TickBox key={r} on={value.ratio === r} label={`${r}R`} onClick={() => onChange({ ...value, items, ratio: value.ratio === r ? null : r })} />)}
      </div>
    </div>
  )
}
// The checklist on the diary page: only what was ticked, written out as words
function ChecklistRead({ value }: { value: Checklist }) {
  const text = checklistText(value)
  return text ? <p className="dp-p">{text}</p> : null
}

// ── One trade: tick each entry pattern's result ──────────────────────────────
// A saved trade read back as a page of the owner's diary
function storyOf(trade: Trade, only: string, name?: string) {
  const types = ENTRY_TYPES.filter(t => (!only || t.poi === only) && trade.results[t.key])
  return buildStory({
    id: trade.id, name, date: trade.trade_date, pair: trade.instrument, direction: trade.direction,
    hasNote: !!trade.notes.trim(), exitDate: trade.exit_date,
    rows: types.map(t => {
      const r = trade.results[t.key]
      return { slot: t.key, label: (only ? t.model : t.label).replace(' (old)', ''), outcome: r.outcome, rr: r.rr, takes: r.takes, exit: r.exit, net: rOf(r) }
    }),
  })
}

function DiaryPage({ trade, num, onEdit, onDelete }: { trade: Trade; num: TradeNum; onEdit: () => void; onDelete: () => void }) {
  const only = useContext(OnlyPoi)
  const { user } = useAuth()
  const imgs = trade.images || {}
  const note = trade.notes.trim()
  const story = storyOf(trade, only, user?.name)
  const pics = (slot: string, label: string) => imgs[slot]?.length
    ? <div className="dp-pics">{imgs[slot].map(id => <Thumb key={id} id={id} label={label} />)}</div>
    : null
  let n = 0
  const line = () => ({ animationDelay: `${(n++) * 0.14}s` })   // each line drifts in after the one before
  const journal = only ? POIS.find(p => p.key === only)?.label : ''
  return (
    <div className="dp-wrap">
      <div className={`dp-page dp-${story.mood}`}>
        {story.sparks.map((e, i) => <span key={i} className={`dp-spark dp-spark${i}`} aria-hidden>{e}</span>)}
        <div className="dp-head dp-line" style={line()}>
          <span className="dp-ribbon">{story.ribbon}</span>
          <span className="dp-stamp">{monthName(trade.trade_date.slice(0, 7)).split(' ')[0]} {tradesWord(num.month)} {num.month} · {trade.trade_date.slice(0, 4)} {tradesWord(num.year)} {num.year} · {journal ? `${journal} · ` : ''}{fmtDay(trade.trade_date)}</span>
        </div>
        <div className="diary-script dp-greet dp-line" style={line()}>{story.greeting}</div>
        <p className="dp-p dp-line" style={line()}>{story.opening}{story.noNote ? ` ${story.noNote}` : ''}</p>
        {note && <div className="dp-note dp-line" style={line()}>{note}</div>}
        {only === 'chk' && checklistText(trade.checklist ?? EMPTY_CHECKLIST) && <div className="dp-line" style={line()}><ChecklistRead value={trade.checklist ?? EMPTY_CHECKLIST} /></div>}
        {imgs[only]?.length ? <div className="dp-line" style={line()}>{pics(only, 'Chart')}</div> : null}
        {story.rows.map(r => (
          <div key={r.slot} className="dp-line" style={line()}>
            <p className="dp-p">{r.text}</p>
            {pics(r.slot, 'Chart')}
          </div>
        ))}
        {/* Pictures on a row with no result ticked, so none go missing from the page */}
        {Object.keys(imgs).filter(k => k !== only && !story.rows.some(r => r.slot === k)).map(k => <div key={k} className="dp-line" style={line()}>{pics(k, 'Chart')}</div>)}
        {story.held && <p className="dp-p dp-line" style={line()}>{story.held}</p>}
        <div className="dp-foot dp-line" style={line()}>
          <div>
            <div className="dp-yours">{story.yours}</div>
            <div className="diary-script dp-sign">{story.signature}</div>
          </div>
          <span style={{ display: 'flex', gap: 6 }}>
            <Chip on={false} color="var(--accent)" bg="var(--accent-bg)" onClick={onEdit}><Pencil size={11} /> Edit this page</Chip>
            <button onClick={() => { if (confirm(`Delete this ${trade.instrument} trade?`)) onDelete() }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, border: '1px solid var(--border)', background: 'transparent', color: 'var(--bearish)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              <Trash2 size={12} /> Delete
            </button>
          </span>
        </div>
      </div>
    </div>
  )
}

function TradeCard({ trade, num, open, onToggle, onChange, onImages, onDelete }: {
  trade: Trade; num: TradeNum; open: boolean; onToggle: () => void
  onChange: (t: Trade) => void; onImages: (images: Record<string, number[]>) => void; onDelete: () => void
}) {
  const only = useContext(OnlyPoi)
  const [customFor, setCustomFor] = useState<string | null>(null)
  const [poi, setPoi] = useState(only || POIS[0].key)
  const [customVal, setCustomVal] = useState('')
  const [picsFor, setPicsFor] = useState<string | null>(null)   // entry row whose image strip is open
  const [pick, setPick] = useState<{ key: string; n: number; at: number }>({ key: '', n: 0, at: 0 })   // 📷 tapped: open the picker on that row
  const [viewing, setViewing] = useState(false)   // reading the page as a story
  const imgs = trade.images || {}
  const setSlot = (slot: string, ids: number[]) => {
    const images = { ...imgs }
    if (ids.length) images[slot] = ids
    else delete images[slot]
    onImages(images)
  }
  // Every picture under a POI: its own and its entries'
  const poiPics = (p: string) => Object.entries(imgs).filter(([k]) => k === p || k.endsWith(`_${p}`)).reduce((n, [, v]) => n + v.length, 0)
  const shownRes = ENTRY_TYPES.filter(t => !only || t.poi === only).map(t => trade.results[t.key]).filter((r): r is EntryResult => !!r)   // hidden old keys not counted
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
    else setResult(key, { outcome: o, rr: (o === 'win' && cur?.outcome === 'win') || (o === 'be' && cur?.outcome === 'be') ? cur?.rr ?? null : null, ...(o !== 'none' && cur?.takes ? { takes: cur.takes } : {}), ...(o !== 'none' && cur?.exit ? { exit: cur.exit } : {}) })
  }

  return (
    <div data-diary-card="" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, marginBottom: 10, overflow: 'hidden' }}>
      <div onClick={() => { if (open) onToggle(); else setViewing(v => !v) }} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', cursor: 'pointer', flexWrap: 'wrap' }}>
        {open || viewing ? <ChevronDown size={16} color="var(--text-muted)" /> : <ChevronRight size={16} color="var(--text-muted)" />}
        <span style={{ fontSize: 13, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
          <b>#{num.month}</b> · {num.year} in {trade.trade_date.slice(0, 4)}
        </span>
        <span style={{ fontWeight: 800, fontSize: 14, color: 'var(--text-primary)' }}>{trade.instrument}</span>
        <span style={{ fontSize: 11, fontWeight: 800, padding: '2px 8px', borderRadius: 6,
          color: trade.direction === 'buy' ? 'var(--bullish)' : 'var(--bearish)',
          background: trade.direction === 'buy' ? 'var(--bullish-bg)' : 'var(--bearish-bg)' }}>{trade.direction.toUpperCase()}</span>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {fmtDay(trade.trade_date)}
          {trade.exit_date && <> → {fmtDay(trade.exit_date)} <span style={{ color: 'var(--text-muted)' }}>· {heldFor(trade.trade_date, trade.exit_date)}</span></>}
        </span>
        {SHOW_H4_ALERT && trade.alert_type && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>· {trade.alert_type}</span>}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          {only === 'chk' ? (() => {
            // The entries tried on this one setup, grouped: how many won, lost or broke even
            const tried = shownRes.filter(r => r.outcome !== 'none')
            const n = (o: Outcome) => tried.filter(r => r.outcome === o).length
            return tried.length ? <>{tried.length} {tried.length === 1 ? 'entry' : 'entries'} tried · <b style={{ color: 'var(--bullish)' }}>{n('win')} W</b> · <b style={{ color: 'var(--loss)' }}>{n('loss')} L</b> · <b style={{ color: '#f59e0b' }}>{n('be')} BE</b></> : <>no entries tried yet</>
          })() : <>
          {done} ticked
          {tradeR.length > 0 && <> · outcome {tradeR.map((v, i) => (
            <span key={i}>{i > 0 && ' / '}<b style={{ color: v > 0 ? 'var(--bullish)' : v < 0 ? 'var(--loss)' : 'var(--text-muted)' }}>{fmtR(v)}</b></span>
          ))}</>}
          </>}
        </span>
        <span onClick={e => e.stopPropagation()} style={{ display: 'flex', gap: 6 }}>
          <Chip on={viewing} color="var(--accent)" bg="var(--accent-bg)" onClick={() => { if (open) onToggle(); setViewing(!viewing) }}><Eye size={12} /> View</Chip>
          <Chip on={open} color="var(--accent)" bg="var(--accent-bg)" onClick={() => { setViewing(false); onToggle() }}><Pencil size={11} /> Edit</Chip>
        </span>
      </div>
      {viewing && !open && <DiaryPage trade={trade} num={num} onEdit={() => { setViewing(false); onToggle() }} onDelete={onDelete} />}
      {open && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '10px 14px 12px' }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
            {POIS.filter(p => !only).map(p => {
              const n = ENTRY_TYPES.filter(t => t.poi === p.key && trade.results[t.key]).length
              return (
                <Chip key={p.key} on={poi === p.key} color="var(--accent)" bg="var(--accent-bg)" onClick={() => setPoi(p.key)}>
                  {p.label}{n ? ` · ${n}` : ''}{poiPics(p.key) ? ` · 📷${poiPics(p.key)}` : ''}
                </Chip>
              )
            })}
          </div>
          {/* H1 / M15 entry: pictures go on LC 1 and LC 2 only. A chart already saved up here still shows, so it can be seen or removed */}
          {(POIS.find(p => p.key === poi)?.old || !!imgs[poi]?.length) && <ImageStrip tradeId={trade.id} slot={poi} label={`${POIS.find(p => p.key === poi)?.label ?? poi} chart`}
            ids={imgs[poi] || []} onChange={ids => setSlot(poi, ids)} />}
          {poi === 'chk' && <ChecklistBox value={trade.checklist ?? EMPTY_CHECKLIST} onChange={c => onChange({ ...trade, checklist: c })} />}
          {ENTRY_TYPES.filter(t => t.poi === poi && (!t.retired || trade.results[t.key] || imgs[t.key]?.length)).map(t => {
            const r = trade.results[t.key]
            return (
              <div key={t.key} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 0', borderBottom: '1px dashed var(--border)', flexWrap: 'wrap' }}>
                <span style={{ flex: '1 1 210px', fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{t.model}</span>
                {OUTCOMES.map(o => (
                  <Chip key={o.key} on={r?.outcome === o.key} color={o.color} bg={o.bg} onClick={() => tapOutcome(t.key, o.key)}>{o.label}</Chip>
                ))}
                <Chip on={picsFor === t.key || !!imgs[t.key]?.length} color="var(--accent)" bg="var(--accent-bg)"
                  onClick={() => { setPicsFor(t.key); setPick(p => ({ key: t.key, n: p.n + 1, at: Date.now() })) }}>
                  📷{imgs[t.key]?.length ? ` ${imgs[t.key].length}` : ''}
                </Chip>
                {(picsFor === t.key || !!imgs[t.key]?.length) && (
                  <ImageStrip compact tradeId={trade.id} slot={t.key} label={t.label} ids={imgs[t.key] || []}
                    onChange={ids => setSlot(t.key, ids)} pickTick={pick.key === t.key ? pick.n : 0} pickAt={pick.at}
                    onCancel={() => setPicsFor(cur => (cur === t.key ? null : cur))} />
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
                        {v != null && <> = <b style={{ color: v > 0 ? 'var(--bullish)' : v < 0 ? 'var(--loss)' : 'var(--text-muted)' }}>{fmtR(v)}</b> overall</>}
                      </span>) })()}
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', margin: '0 2px 0 12px' }} title="When this entry's trade was closed">Exit</span>
                    <DateText withTime value={r.exit} min={trade.trade_date}
                      onChange={v => { const { exit: _x, ...rest } = r; setResult(t.key, v ? { ...rest, exit: v } : rest) }} />
                    {r.exit && (
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        <b>{weekday(r.exit.slice(0, 10))}</b> {r.exit.slice(11, 16)} · <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{heldFor(trade.trade_date, r.exit.slice(0, 10))}</span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Edit the trade's details: pair, date, direction, H4 alert (each saves straight away) */}
            <span style={{ fontSize: 11, color: 'var(--text-muted)', flexBasis: '100%' }}>Trade details</span>
            <input defaultValue={trade.instrument} title="Pair (fix a spelling mistake here)"
              onInput={e => { e.currentTarget.value = cleanPair(e.currentTarget.value) }}
              onBlur={e => { const p = cleanPair(e.target.value); if (p && p !== trade.instrument) onChange({ ...trade, instrument: p }); else e.target.value = trade.instrument }}
              style={{ ...selStyle, width: 110 }} />
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              Entry
              <DateText value={trade.trade_date} onChange={v => v && onChange({ ...trade, trade_date: v })} />
              <b style={{ color: 'var(--text-secondary)', minWidth: 28 }}>{weekday(trade.trade_date)}</b>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              Exit
              <DateText value={trade.exit_date} min={trade.trade_date} onChange={v => onChange({ ...trade, exit_date: v || null })} />
              {trade.exit_date && <b style={{ color: 'var(--text-secondary)', minWidth: 28 }}>{weekday(trade.exit_date)}</b>}
              {trade.exit_date && <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{heldFor(trade.trade_date, trade.exit_date)}</span>}
            </label>
            <Chip on={trade.direction === 'buy'} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => trade.direction !== 'buy' && onChange({ ...trade, direction: 'buy' })}>BUY</Chip>
            <Chip on={trade.direction === 'sell'} color="var(--bearish)" bg="var(--bearish-bg)" onClick={() => trade.direction !== 'sell' && onChange({ ...trade, direction: 'sell' })}>SELL</Chip>
            {SHOW_H4_ALERT && <select value={trade.alert_type} title="H4 alert" onChange={e => onChange({ ...trade, alert_type: e.target.value })} style={selStyle}>
              {!ALERT_TYPES.includes(trade.alert_type) && <option value={trade.alert_type}>{trade.alert_type || '—'}</option>}
              {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
            </select>}
            <textarea defaultValue={trade.notes} placeholder="Notes (optional)" rows={3}
              onInput={e => { const t = e.currentTarget; t.style.height = 'auto'; t.style.height = `${t.scrollHeight + 2}px` }}
              ref={t => { if (t && !t.dataset.sized) { t.dataset.sized = '1'; t.style.height = 'auto'; t.style.height = `${Math.max(t.scrollHeight + 2, 72)}px` } }}
              onBlur={e => e.target.value !== trade.notes && onChange({ ...trade, notes: e.target.value })}
              style={{ ...selStyle, flexBasis: '100%', width: '100%', minHeight: 72, resize: 'vertical', lineHeight: 1.5, fontFamily: 'inherit' }} />
            <button onClick={() => { if (confirm(`Delete this ${trade.instrument} trade?`)) onDelete() }}
              style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'transparent', color: 'var(--bearish)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              <Trash2 size={13} /> Delete
            </button>
            <button onClick={onToggle}
              style={{ display: 'flex', alignItems: 'center', gap: 5, marginLeft: 'auto', padding: '8px 18px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>
              <Check size={14} /> Save
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── The diary cover (journal pages) ───────────────────────────────────────────
const DIARY_QUOTES = [
  'Patience is my superpower ✨',
  'I wait for my level, and I trust my plan 🌸',
  'Every trade is a page; every page makes me wiser 📖',
  'Calm mind, clear chart, kind heart 💖',
  'Small steps, golden results 🌟',
  'The market rewards the ones who wait 🦋',
  'I protect my capital like a treasure 👑',
]
const SPARKS: { t: string; top: string; left?: string; right?: string; size: number; delay: string }[] = [
  { t: '✨', top: '14%', left: '62%', size: 18, delay: '0s' },
  { t: '🌸', top: '62%', left: '88%', size: 20, delay: '1.1s' },
  { t: '⭐', top: '22%', right: '12%', size: 14, delay: '0.6s' },
  { t: '🦋', top: '68%', left: '70%', size: 18, delay: '2s' },
  { t: '✨', top: '40%', right: '4%', size: 12, delay: '1.6s' },
  { t: '🌙', top: '10%', right: '24%', size: 16, delay: '2.6s' },
]
// The diary's look, chosen on its cover and remembered in this browser
const DIARY_PALETTES: { key: string; name: string; dot: string }[] = [
  { key: 'purple', name: 'Purple', dot: 'linear-gradient(135deg, #9B5DE5, #E07AC0)' },
  { key: 'ice', name: 'Ice', dot: 'linear-gradient(135deg, #3E9BD6, #C4E6FB)' },
  { key: 'pink', name: 'Pink', dot: 'linear-gradient(135deg, #E0679F, #FFC4DE)' },
  { key: 'peach', name: 'Peach', dot: 'linear-gradient(135deg, #EE8456, #FFD7C4)' },
  { key: 'mint', name: 'Mint', dot: 'linear-gradient(135deg, #35B193, #C2EFE0)' },
]
interface DiaryLook { palette: string; text: 'italic' | 'script' | 'plain'; size: 'petite' | 'cosy' }
const DIARY_DEFAULT: DiaryLook = { palette: 'purple', text: 'italic', size: 'petite' }
function useDiaryLook(): [DiaryLook, (l: DiaryLook) => void] {
  const [look, setLook] = useState<DiaryLook>(DIARY_DEFAULT)
  useEffect(() => {
    try { setLook({ ...DIARY_DEFAULT, ...JSON.parse(localStorage.getItem('mbp_diary_look') || '{}') }) } catch { /* private mode */ }
  }, [])
  const set = (l: DiaryLook) => { setLook(l); try { localStorage.setItem('mbp_diary_look', JSON.stringify(l)) } catch { /* private mode */ } }
  return [look, set]
}

function DiaryCover({ title, sub, trades, look, setLook }: { title: string; sub: string; trades: Trade[]; look: DiaryLook; setLook: (l: DiaryLook) => void }) {
  const { user } = useAuth()
  const name = user?.name?.trim()
  const [greet, setGreet] = useState('Hello')
  const [quote, setQuote] = useState(DIARY_QUOTES[0])
  useEffect(() => {
    const h = new Date().getHours()
    const who = name ? `, ${name}` : ''
    setGreet(h < 12 ? `Good morning${who} ☀️` : h < 17 ? `Good afternoon${who} 🌷` : `Good evening${who} 🌙`)
    setQuote(DIARY_QUOTES[Math.floor(Date.now() / 86400000) % DIARY_QUOTES.length])   // a new one each day
  }, [name])
  let wins = 0
  for (const t of trades) for (const r of Object.values(t.results || {})) if (r.outcome === 'win') wins++
  return (
    <div className="diary-cover">
      <div className="diary-ribbon" />
      {SPARKS.map((s, i) => (
        <span key={i} className="diary-spark" aria-hidden
          style={{ top: s.top, left: s.left, right: s.right, fontSize: s.size, animationDelay: s.delay }}>{s.t}</span>
      ))}
      <div className="diary-greet">{greet}</div>
      <h1 className="diary-script">{title}</h1>
      <p className="diary-sub">{sub}</p>
      <div className="diary-quote diary-script">“{quote}”</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        {[`📖 ${trades.length} page${trades.length === 1 ? '' : 's'} written`, `💖 ${wins} win${wins === 1 ? '' : 's'} ticked`].map(x => (
          <span key={x} style={{ fontSize: 12, fontWeight: 700, padding: '5px 12px', borderRadius: 999,
            background: 'color-mix(in srgb, var(--surface) 70%, transparent)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>{x}</span>
        ))}
      </div>
      <div className="diary-style">
        <span>🎀 Colour</span>
        {DIARY_PALETTES.map(p => (
          <button key={p.key} title={p.name} aria-label={p.name} className={`sw${look.palette === p.key ? ' on' : ''}`}
            style={{ background: p.dot }} onClick={() => setLook({ ...look, palette: p.key })} />
        ))}
        <span className="sep" />
        <span>Summary</span>
        {([['italic', 'Italic'], ['script', 'Handwritten'], ['plain', 'Plain']] as const).map(([k, n]) => (
          <button key={k} className={`chip${look.text === k ? ' on' : ''}`} onClick={() => setLook({ ...look, text: k })}>{n}</button>
        ))}
        <span className="sep" />
        <span>Size</span>
        {([['petite', 'Petite'], ['cosy', 'Cosy']] as const).map(([k, n]) => (
          <button key={k} className={`chip${look.size === k ? ' on' : ''}`} onClick={() => setLook({ ...look, size: k })}>{n}</button>
        ))}
      </div>
    </div>
  )
}

// ── The journal as a book (saved as a PDF from the browser's print box) ──────
const BOOK_INK: Record<string, [string, string]> = {
  purple: ['#7B3FC9', '#E4D2FF'], ice: ['#2479B3', '#CFE9FB'], pink: ['#C44D86', '#FFD3E6'], peach: ['#D0663A', '#FFE0D0'], mint: ['#1F9176', '#CFF3E7'],
}
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
async function fetchPicture(id: number): Promise<BookPicture> {
  try {
    const r = await fetch(`${API_BASE}/api/entry-tests/images/${id}`, { headers: authHdr() })
    if (!r.ok) return { src: null }
    const b = await r.blob()
    return { src: await new Promise<string>((ok, no) => {
      const f = new FileReader()
      f.onload = () => ok(String(f.result))
      f.onerror = no
      f.readAsDataURL(b)
    }) }
  } catch { return { src: null } }
}
// A few at a time, so a long journal doesn't flood the server
async function fetchPictures(ids: number[]): Promise<Map<number, BookPicture>> {
  const out = new Map<number, BookPicture>()
  const todo = [...ids]
  await Promise.all(Array.from({ length: 4 }, async () => {
    for (let id = todo.shift(); id != null; id = todo.shift()) out.set(id, await fetchPicture(id))
  }))
  return out
}
function periodSummary(list: Trade[], only: string): string {
  let w = 0, l = 0, be = 0, r = 0
  for (const tr of list)
    for (const t of ENTRY_TYPES) {
      const x = tr.results[t.key]
      if (!x || (only && t.poi !== only)) continue
      const e = entriesIn(x)
      w += e.w; l += e.l; be += e.be
      r += rOf(x) ?? 0
    }
  const buys = list.filter(t => t.direction === 'buy').length
  if (only === 'chk') return `${plural(list.length, 'setup')} taken · ${plural(buys, 'buy')} · ${plural(list.length - buys, 'sell')}`
  const entries = w + l + be
  return `${plural(list.length, 'setup')} · ${entries} ${entries === 1 ? 'entry' : 'entries'} · ${plural(buys, 'buy')} · ${plural(list.length - buys, 'sell')} · ${w} W · ${l} L · ${be} BE · ${fmtR(r)}`
}
function resultWord(t: Trade, only: string): string {
  return ENTRY_TYPES.filter(e => (!only || e.poi === only) && t.results[e.key]).map(e => {
    const x = t.results[e.key]
    if (x.outcome === 'none') return 'No entry'
    const v = rOf(x)
    return `${x.outcome === 'win' ? 'Win' : x.outcome === 'loss' ? 'Loss' : 'BE'}${v != null ? ` ${fmtR(v)}` : ''}`
  }).join(', ')
}
type BookOptions = { list: Trade[]; only: string; name?: string; title: string; palette: string; filterNote: string; nums: Map<number, TradeNum> }
async function bookInput(opt: BookOptions): Promise<BookInput> {
  const { list, only, name, title, palette, filterNote, nums } = opt
  const chrono = [...list].sort((a, b) => a.trade_date.localeCompare(b.trade_date) || a.id - b.id)
  const pictures = await fetchPictures(chrono.flatMap(t => Object.values(t.images || {}).flat()))
  const take = (ids?: number[]) => (ids || []).map(id => pictures.get(id) ?? { src: null })
  const chapters: BookChapter[] = []
  for (const t of chrono) {
    const key = t.trade_date.slice(0, 7)
    const monthTitle = monthName(key)
    let c = chapters[chapters.length - 1]
    if (!c || c.title !== monthTitle) { c = { title: monthTitle, summary: '', pages: [] }; chapters.push(c) }
    const story = storyOf(t, only, name)
    const imgs = t.images || {}
    const n = nums.get(t.id) ?? NO_NUM
    const page: BookPage = {
      monthNum: n.month, yearNum: n.year, monthWord: monthTitle.split(' ')[0], year: key.slice(0, 4), dayLabel: fmtDay(t.trade_date),
      pair: t.instrument, direction: t.direction, note: t.notes.trim(), story,
      topPictures: take(imgs[only]),
      rows: story.rows.map(r => ({ text: r.text, pictures: take(imgs[r.slot]) })),
      otherPictures: take(Object.keys(imgs).filter(k => k !== only && !story.rows.some(r => r.slot === k)).flatMap(k => imgs[k])),
      resultWord: resultWord(t, only),
      ...(only === 'chk' ? {
        checklist: checklistText(t.checklist ?? EMPTY_CHECKLIST),
      } : {}),
    }
    c.pages.push(page)
  }
  for (const c of chapters) c.summary = periodSummary(chrono.filter(t => monthName(t.trade_date.slice(0, 7)) === c.title), only)
  const [ink, soft] = BOOK_INK[palette] || BOOK_INK.purple
  const firstM = chapters[0]?.title || '', lastM = chapters[chapters.length - 1]?.title || ''
  return {
    title, owner: name?.trim() || 'My diary',
    span: firstM === lastM ? firstM : `${firstM} to ${lastM}`,
    stats: periodSummary(chrono, only), filterNote, accent: ink, accentSoft: soft, chapters,
  }
}
async function printBook(w: Window, opt: BookOptions) {
  const html = bookHtml(await bookInput(opt))
  w.document.open()
  w.document.write(html)
  w.document.close()
  // Print once the pictures and the handwriting font are really there, or they come out blank
  const imgs = Array.from(w.document.images)
  await Promise.all(imgs.map(i => i.complete ? null : new Promise(ok => { i.onload = ok; i.onerror = ok })))
  await Promise.race([w.document.fonts.ready, new Promise(ok => setTimeout(ok, 4000))])
  w.focus()
  w.print()
}

// ── Page ──────────────────────────────────────────────────────────────────────
// book "backtest" (Backtest page, every POI) or a live journal on the Trading Journal
// page: "live_engulfing" / "live_h4_key", each its own trades, limited to that POI
type Book = 'backtest' | 'bt_engulfing' | 'bt_h4_key' | 'live_engulfing' | 'live_h4_key' | 'bt_scl' | 'bt_hl_liq' | 'live_scl' | 'live_hl_liq' | 'bt_check' | 'live_check'
const JOURNAL: Record<Book, { title: string; poi: string }> = {
  backtest: { title: 'Entry Tester', poi: '' },
  bt_engulfing: { title: 'Engulfing Journal', poi: 'engulfing' },
  bt_h4_key: { title: 'Fresh Key Levels Journal', poi: 'h4_key' },
  live_engulfing: { title: 'Engulfing Journal', poi: 'engulfing' },
  live_h4_key: { title: 'Fresh Key Levels Journal', poi: 'h4_key' },
  bt_scl: { title: 'H1 Entry Journal', poi: 'scl' },
  bt_hl_liq: { title: 'M15 Entry Journal', poi: 'hl_liq' },
  live_scl: { title: 'H1 Entry Journal', poi: 'scl' },
  live_hl_liq: { title: 'M15 Entry Journal', poi: 'hl_liq' },
  bt_check: { title: 'Checklist Journal', poi: 'chk' },
  live_check: { title: 'Checklist Journal', poi: 'chk' },
}
// The diary cover's handwritten title for each journal
const DIARY_TITLE: Partial<Record<Book, string>> = {
  bt_engulfing: 'My Engulfing Backtest Diary', bt_h4_key: 'My Fresh Key Levels Backtest Diary',
  live_engulfing: 'My Engulfing Diary', live_h4_key: 'My Fresh Key Levels Diary',
  bt_scl: 'My H1 Entry Backtest Diary', bt_hl_liq: 'My M15 Entry Backtest Diary',
  live_scl: 'My H1 Entry Diary', live_hl_liq: 'My M15 Entry Diary',
  bt_check: 'My Checklist Backtest Diary', live_check: 'My Checklist Diary',
}
export default function EntryTester({ tabs, book = 'backtest' }: { tabs?: React.ReactNode; book?: Book }) {
  const live = book.startsWith('live')
  const jr = JOURNAL[book]
  const diary = !!jr.poi   // the Engulfing / Fresh Key Levels journals
  const [look, setLook] = useDiaryLook()
  const { user } = useAuth()
  const [booking, setBooking] = useState('')   // what the book buttons are busy with
  const bq = `?book=${book}`
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [openId, setOpenId] = useState<number | null>(null)
  // New-trade bar: remembers the last pair / alert so the next one is one tap
  const [pair, setPair] = useState('')
  const [typing, setTyping] = useState(false)   // "Other…": a pair that isn't in the list
  const [date, setDate] = useState('')   // no date is filled in for you
  const [dir, setDir] = useState<'buy' | 'sell'>('buy')
  const [alertType, setAlertType] = useState('')
  // Filters for the scoreboard and list
  const [fPair, setFPair] = useState('')
  const [fAlert, setFAlert] = useState('')
  const [fDir, setFDir] = useState('')

  useEffect(() => {
    setPair(cleanPair(load('mbp_et_pair', 'XAUUSD')) || 'XAUUSD')
    setAlertType(load('mbp_et_alert', 'Origin'))
    fetch(`${API_BASE}/api/entry-tests${bq}`, { headers: hdrs() })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((d: Trade[]) => setTrades(d))   // every trade starts folded; tap one to open it
      .catch(() => setErr('Could not load your entry tests.'))
      .finally(() => setLoading(false))
  }, [bq])

  function body(t: Omit<Trade, 'id'>) { return JSON.stringify({
    trade_date: t.trade_date, instrument: t.instrument, direction: t.direction,
    alert_type: t.alert_type, notes: t.notes, results: t.results, exit_date: t.exit_date || null,
    ...(t.checklist ? { checklist: t.checklist } : {}),
  }) }

  const addTrade = async () => {
    const p = cleanPair(pair)
    if (!p) return
    if (!date) { setErr('Type the trade date first: dd/mm/yy.'); return }
    save('mbp_et_pair', p)
    save('mbp_et_alert', alertType)
    const r = await fetch(`${API_BASE}/api/entry-tests${bq}`, {
      method: 'POST', headers: hdrs(),
      body: body({ trade_date: date, instrument: p, direction: dir, alert_type: SHOW_H4_ALERT ? alertType : '', notes: '', results: {}, images: {} }),
    })
    if (!r.ok) { setErr('Could not add the trade.'); return }
    const t: Trade = await r.json()
    setTrades(prev => [t, ...prev])
    setOpenId(t.id)
    setDate('')
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

  const removeAll = async () => {
    const typed = prompt(`This deletes ALL ${trades.length} ${jr.title} trades, with their ticks, notes and chart images. It can't be undone.\n\nType DELETE to confirm.`)
    if (typed !== 'DELETE') return
    const r = await fetch(`${API_BASE}/api/entry-tests/delete-all${bq}`, { method: 'POST', headers: hdrs(), body: JSON.stringify({ confirm: 'DELETE' }) })
    if (r.ok) { setTrades([]); setOpenId(null); setErr('') }
    else setErr('Could not delete the trades. Try again.')
  }

  const remove = async (id: number) => {
    const r = await fetch(`${API_BASE}/api/entry-tests/${id}`, { method: 'DELETE', headers: hdrs() })
    if (r.ok) setTrades(prev => prev.filter(x => x.id !== id))
  }

  const shown = trades.filter(t => (!fPair || t.instrument === fPair) && (!fAlert || t.alert_type === fAlert) && (!fDir || t.direction === fDir))
  const pairs = Array.from(new Set(trades.map(t => t.instrument))).sort()
  // The Checklist journal counts setups: its entry rows are samples of one trade, so each setup is one number
  const tradeNum = useMemo(() => numberTrades(trades, jr.poi === 'chk'), [trades, jr.poi])
  // The newest month you've logged is still running; earlier months are complete
  const latestMonth = trades.reduce((m, t) => (t.trade_date.slice(0, 7) > m ? t.trade_date.slice(0, 7) : m), '')
  // The remembered pair stays selectable even if it isn't in the standard list
  const stdPairs = INSTRUMENTS.map(i => i.replace('/', ''))
  const pairOptions = Array.from(new Set([...(pair && !typing ? [pair] : []), ...stdPairs]))
  // A pair typed under "Other…" that has no trades yet can be removed again
  const customPair = !typing && !!pair && !stdPairs.includes(pair) && !pairs.includes(pair)
  const removePair = () => { setPair('XAUUSD'); save('mbp_et_pair', 'XAUUSD') }
  const bookOptions = (): BookOptions => ({
    list: shown, only: jr.poi, name: user?.name, title: DIARY_TITLE[book] || jr.title, palette: look.palette, nums: tradeNum,
    filterNote: [fPair, fDir === 'buy' ? 'Buys only' : fDir === 'sell' ? 'Sells only' : ''].filter(Boolean).join(' · '),
  })
  // Straight to the device: a real PDF file
  const downloadBook = async () => {
    setBooking('Gathering your pictures…')
    setErr('')
    try {
      const opt = bookOptions()
      const input = await bookInput(opt)
      await downloadBookPdf(input, `${input.title} - ${input.owner}.pdf`.replace(/[\\/:*?"<>|]/g, ''), (done, total) => setBooking(`Making page ${done} of ${total}…`))
    } catch {
      setErr('Could not make the PDF. Try again, or use Print.')
    } finally {
      setBooking('')
    }
  }
  // The browser's print box, for paper
  const printTheBook = async () => {
    // Opened straight from the tap, or the browser blocks it as a pop-up
    const w = window.open('', '_blank')
    if (!w) { setErr('Your browser blocked the new tab for the book. Allow pop-ups for this site, then tap again.'); return }
    w.document.write(BOOK_WAIT)
    w.document.close()
    setBooking('Preparing your book…')
    setErr('')
    try {
      await printBook(w, bookOptions())
    } catch {
      w.close()
      setErr('Could not prepare the book. Try again.')
    } finally {
      setBooking('')
    }
  }

  return (
    <div className={diary ? `fairy-diary dp-${look.palette} dt-${look.text} ds-${look.size}` : undefined}
      style={{ minHeight: '100vh', background: diary ? undefined : 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <TopBar title={jr.title} />
      <OnlyPoi.Provider value={jr.poi}>
      <main style={{ flex: 1, width: '100%', padding: '20px 24px', maxWidth: 1100 }}>
        {tabs}
        {diary ? (
          <DiaryCover title={DIARY_TITLE[book] || jr.title} trades={trades} look={look} setLook={setLook}
            sub={`Only you can read this diary. ${live ? 'Your live trades, kept apart from the backtest.' : 'Your backtested trades, kept apart from your live journals.'} For each trade, tap how every confirmation model did. Each tap is saved, like ink on the page.`} />
        ) : (
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <FlaskConical size={20} color="var(--accent)" /> {jr.title}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>
            Only you see this. {live ? 'Your live trades, kept apart from the backtest. ' : jr.poi ? 'Your backtested trades, kept apart from your live journals. ' : ''}{jr.poi ? 'For each trade, tap how every confirmation model did on that same trade. ' : 'For each trade, tap how every entry pattern did on that same trade. '}Each tap saves.
          </p>
        </div>
        )}

        {/* New trade */}
        {diary && <div className="diary-script" style={{ fontSize: 20, color: 'var(--accent-hover)', margin: '0 0 6px 6px' }}>Dear diary, today I took… ✍️</div>}
        <div data-diary-card="" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 12, marginBottom: 20 }}>
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
          <DateText value={date} onChange={v => v && setDate(v)} />
          {date && <b style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{weekday(date)}</b>}
          <Chip on={dir === 'buy'} color="var(--bullish)" bg="var(--bullish-bg)" onClick={() => setDir('buy')}>BUY</Chip>
          <Chip on={dir === 'sell'} color="var(--bearish)" bg="var(--bearish-bg)" onClick={() => setDir('sell')}>SELL</Chip>
          {SHOW_H4_ALERT && <select value={alertType} onChange={e => setAlertType(e.target.value)} style={selStyle}>
            {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
          </select>}
          <button onClick={addTrade} className={diary ? 'diary-add' : undefined} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontSize: 13, fontWeight: 700, marginLeft: 'auto' }}>
            <Plus size={14} /> {diary ? 'Add to my diary' : 'Add trade'}
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
            {SHOW_H4_ALERT && <select value={fAlert} onChange={e => setFAlert(e.target.value)} style={selStyle}>
              <option value="">All H4 alerts</option>
              {ALERT_TYPES.map(a => <option key={a} value={a}>{a}</option>)}
            </select>}
            <select value={fDir} onChange={e => setFDir(e.target.value)} style={selStyle}>
              <option value="">Buys and sells</option>
              <option value="buy">Buys</option>
              <option value="sell">Sells</option>
            </select>
            <span style={{ display: 'flex', gap: 8, marginLeft: 'auto', alignItems: 'center', flexWrap: 'wrap' }}>
              {booking && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{booking}</span>}
              <button onClick={downloadBook} disabled={!!booking || shown.length === 0} title="Save the trades showing to this device as a PDF book"
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: booking ? 'wait' : 'pointer', fontSize: 13, fontWeight: 700, opacity: booking ? 0.6 : 1 }}>
                <Download size={14} /> Download PDF
              </button>
              <button onClick={printTheBook} disabled={!!booking || shown.length === 0} title="Open the trades showing as a book, ready to print"
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border)', background: 'transparent', color: 'var(--accent)', cursor: booking ? 'wait' : 'pointer', fontSize: 13, fontWeight: 700, opacity: booking ? 0.6 : 1 }}>
                <Printer size={14} /> Print
              </button>
            </span>
          </div>
        )}

        {/* Your trades first (this is where you tick), the results summary under them */}
        {loading ? <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>
          : trades.length === 0 ? (
            <div data-diary-card="" style={{ background: 'var(--card)', border: '1px dashed var(--border)', borderRadius: 12, padding: '18px 20px', marginBottom: 20, color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7 }}>
              <div className={diary ? 'diary-script' : undefined} style={{ fontWeight: 800, color: 'var(--text-primary)', marginBottom: 6, fontSize: diary ? 24 : undefined }}>{diary ? 'Your first page is waiting 🌸' : 'How to log a trade'}</div>
              <div><b>1.</b> In the bar above, pick the <b>pair</b>, the <b>date</b>, <b>BUY</b> or <b>SELL</b>{SHOW_H4_ALERT ? <>, and the <b>H4 alert</b> it came from</> : ''}.</div>
              <div><b>2.</b> Tap <b>Add trade</b>. The trade opens right here.</div>
              <div><b>3.</b> {jr.poi ? <>Tap</> : <>Pick the entry model tab, then tap</>} <b>Win</b>, <b>Loss</b>, <b>BE</b> or <b>No entry</b> on each {jr.poi ? 'confirmation model' : 'entry model'}. On a win, tap the RR.</div>
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
                  {/* A month is a dropdown: its report, then its trades inside it */}
                  <Scoreboard kind="month" title={monthName(m.key)} trades={m.trades}
                    note={m.key === latestMonth ? 'month so far' : undefined}
                    openWith={m.trades.some(t => t.id === openId)}>
                    {m.trades.map(t => (
                      <TradeCard key={t.id} trade={t} num={tradeNum.get(t.id) ?? NO_NUM} open={openId === t.id}
                        onToggle={() => setOpenId(openId === t.id ? null : t.id)}
                        onChange={update} onDelete={() => remove(t.id)}
                        onImages={images => setTrades(prev => prev.map(x => x.id === t.id ? { ...x, images } : x))} />
                    ))}
                  </Scoreboard>
                </div>
              ))}
            </div>
          ))}</div>}

        {trades.length > 0 && <Scoreboard trades={shown} />}

        {/* Start afresh: one button instead of deleting trades one by one */}
        {trades.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4, marginBottom: 30 }}>
            <button onClick={removeAll}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border)',
                background: 'transparent', color: 'var(--bearish)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              <Trash2 size={13} /> Delete all {trades.length} trades (start afresh)
            </button>
          </div>
        )}
      </main>
      </OnlyPoi.Provider>
    </div>
  )
}
