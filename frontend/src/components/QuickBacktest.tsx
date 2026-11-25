'use client'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Zap, Star, Trash2, Pencil, Minus, Plus, Loader2, Trophy, CalendarDays, ChevronDown, Wand2, Camera, Check, X, BookOpen } from 'lucide-react'
import { useTimezone } from '@/lib/timezone'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { buildStory } from '@/lib/diaryStory'

// Owner only (2026-11-21): one fast pass through the years. For each setup (breakout → liquidity → POI) tick which
// H1 confirmations formed, how each ended and how many times it was taken; star the first one to form.
// TP 3R, breakeven at 2R. Takes before the last count as losses (as in the Entry Tester). API: api/quick_backtest.py

function api(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}), 'Content-Type': 'application/json' },
  })
}

type Outcome = 'win' | 'be' | 'loss'
interface Res { outcome: Outcome | ''; takes: number; after_tp?: boolean; entered?: string; exit?: string }   // '' only in the form: ticked, result not picked yet
interface Setup {
  id: number; pair: string; date: string; side: 'buy' | 'sell'; range_type: 'inside' | 'opposite'; valid: boolean
  results: Record<string, Res>; first: string | null; tp_r: number; note: string
  auto?: boolean; reviewed?: boolean; pictures?: number; level?: number | null
}
interface Draft {
  pair: string; date: string; side: '' | 'buy' | 'sell'; range_type: '' | 'inside' | 'opposite'; valid: boolean
  results: Record<string, Res>; first: string | null; note: string
}

const CONFS: [string, string][] = [['pcl', 'H1 PCL'], ['eng', 'H1 Engulfing'], ['octgd1', 'H1 OCTGD 1'], ['octgd2', 'H1 OCTGD 2'], ['cisd', 'H1 CISD'], ['octgd15', 'M15 OCTGD'], ['octgd215', 'M15 OCTGD 2'], ['cisd15', 'M15 CISD'], ['cisd5', 'M5 CISD']]
const LABEL = Object.fromEntries(CONFS)
const SHORT: Record<string, string> = { pcl: 'PCL', eng: 'EG', octgd1: 'OC1', octgd2: 'OC2', cisd: 'H1 CISD', octgd15: 'M15 OCTGD', octgd215: 'M15 OCTGD 2', cisd15: 'M15 CISD', cisd5: 'M5 CISD' }
const OUT: [Outcome, string, string][] = [['win', 'Win', 'var(--bullish)'], ['be', 'BE', '#eab308'], ['loss', 'Loss', 'var(--bearish)']]
const LAST_KEY = 'mbp_qbt_last'   // remembers the date / pair / range of the last saved setup

const rOf = (r: Res, tp: number) => r.outcome === 'win' ? tp - (r.takes - 1) : r.outcome === 'be' ? -(r.takes - 1)
  : r.outcome === 'loss' ? -r.takes : 0
const fmtR = (v: number) => `${v > 0 ? '+' : ''}${Math.round(v * 10) / 10}R`
const fmtDay = (d: string) => {
  const [y, m, dd] = d.split('-').map(Number)
  return `${dd} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1]} ${y}`
}

// Date field that always reads day / month / year (the browser's own date input follows the PC's locale,
// which showed month first). Type the digits, or use the calendar button. Stores ISO yyyy-mm-dd.
const isoToDmy = (iso: string) => { const [y, m, d] = iso.split('-'); return y && m && d ? `${d}/${m}/${y}` : '' }
function DateDMY({ value, onChange }: { value: string; onChange: (iso: string) => void }) {
  const [text, setText] = useState(isoToDmy(value))
  const pickRef = useRef<HTMLInputElement>(null)
  useEffect(() => { setText(isoToDmy(value)) }, [value])
  // 7/1/20, 7.1.2020, 07-01-20 ... (day / month / year; a 2-digit year is 20xx). User 2026-11-24: "quick access"
  const parseShort = (t: string): string | null => {
    const m = t.trim().match(/^(\d{1,2})[\/.\- ](\d{1,2})[\/.\- ](\d{2}|\d{4})$/)
    if (!m) return null
    const d = +m[1], mo = +m[2], y = m[3].length === 2 ? 2000 + +m[3] : +m[3]
    const dt = new Date(Date.UTC(y, mo - 1, d))
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null
    return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  }
  const commit = () => { const iso = parseShort(text); if (iso) { onChange(iso); setText(isoToDmy(iso)) } }
  const type = (raw: string) => {
    if (/[\/.\- ]/.test(raw)) {           // typed with separators: keep what she types, take it once it's a full date
      setText(raw.slice(0, 10))
      const iso = parseShort(raw)
      if (iso) onChange(iso)
      return
    }
    const dg = raw.replace(/\D/g, '').slice(0, 8)
    const t = dg.length > 4 ? `${dg.slice(0, 2)}/${dg.slice(2, 4)}/${dg.slice(4)}` : dg.length > 2 ? `${dg.slice(0, 2)}/${dg.slice(2)}` : dg
    setText(t)
    if (dg.length === 8) {
      const d = +dg.slice(0, 2), m = +dg.slice(2, 4), y = +dg.slice(4)
      const dt = new Date(Date.UTC(y, m - 1, d))
      if (dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d)
        onChange(`${dg.slice(4)}-${dg.slice(2, 4)}-${dg.slice(0, 2)}`)
    }
  }
  const bad = text.length >= 6 && isoToDmy(value) !== text && parseShort(text) === null && text.length === 10
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <input value={text} onChange={e => type(e.target.value)} onBlur={commit} onKeyDown={e => { if (e.key === 'Enter') commit() }}
        placeholder="DD/MM/YYYY" title="Type 7/1/20 or 07/01/2020 (day/month/year)" inputMode="numeric"
        style={{ ...field, width: 150, paddingRight: 36, borderColor: bad ? 'var(--bearish)' : undefined }} aria-label="Setup date (day/month/year)" />
      <button type="button" aria-label="Pick from calendar" onClick={() => { try { pickRef.current?.showPicker() } catch { pickRef.current?.focus() } }}
        style={{ position: 'absolute', right: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', display: 'flex' }}>
        <CalendarDays size={16} /></button>
      <input ref={pickRef} type="date" value={value} onChange={e => e.target.value && onChange(e.target.value)} tabIndex={-1} aria-hidden
        style={{ position: 'absolute', right: 0, bottom: 0, width: 1, height: 1, opacity: 0, pointerEvents: 'none' }} />
    </span>
  )
}

// ---- Auto-check (2026-11-23): she gives the POI box and when the watch starts; the server finds every confirmation
// with the Entry Confirmations script's rules on real minute candles and plays each trade (api/autobacktest.py)
interface AutoTrade { time: string; entry: number; sl: number; tp: number; outcome: string; exit: string | null; limit?: boolean; filled?: string | null }
interface AutoRes { results: Record<string, { outcome: string; takes: number; trades: AutoTrade[]; after_tp?: boolean }>; first: string | null; first_tp_at?: string | null
  poi_failed_at: string | null; watched_until: string; trigger_date?: string; setup_end?: string; end_reason?: string; armed_at?: string | null; note: string }

const heldFor = (from?: string | null, to?: string | null): string => {
  if (!from || !to) return ''
  const mins = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 60000))
  const d = Math.floor(mins / 1440), h = Math.floor((mins % 1440) / 60), m = mins % 60
  return d ? `${d} day${d === 1 ? '' : 's'}${h ? ` ${h}h` : ''}` : h ? `${h}h${m ? ` ${m}m` : ''}` : `${m}m`
}

// a wall-clock date + time in an IANA timezone -> ISO 8601 in UTC
function zonedIso(dateIso: string, hhmm: string, tz: string): string {
  const [y, m, d] = dateIso.split('-').map(Number)
  const [hh, mi] = hhmm.split(':').map(Number)
  const guess = Date.UTC(y, m - 1, d, hh || 0, mi || 0)
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(new Date(guess)).map(p => [p.type, p.value]))
  const shown = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute)
  return new Date(guess - (shown - guess)).toISOString()
}

function AutoCheck({ draft, onSaved, onRead, onReviewed }: { draft: Draft; onSaved: (r: AutoRes & { saved_id?: number; pictures?: number }) => void
  onRead: (id: number) => void; onReviewed: (id: number) => Promise<void> }) {
  const { timezone } = useTimezone()
  const [level, setLevel] = useState('')
  const [mode, setMode] = useState<'limit' | 'instant'>('limit')
  const [tol, setTol] = useState('1')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [res, setRes] = useState<(AutoRes & { saved_id?: number; pictures?: number }) | null>(null)
  const [done, setDone] = useState(false)
  const [cov, setCov] = useState<{ pct: number; next_missing: string | null } | null>(null)
  useEffect(() => {
    api(`/api/quick-bt/auto/status?pair=${draft.pair || 'EURUSD'}`).then(r => r.ok ? r.json() : null).then(setCov).catch(() => {})
  }, [draft.pair])
  const when = (iso: string | null) => !iso ? '—' : new Date(iso).toLocaleString('en-GB',
    { timeZone: timezone || 'UTC', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  const go = async () => {
    setErr('')
    if (!draft.side) return setErr('Pick Buy or Sell first')
    if (!draft.range_type) return setErr('Pick Inside range or Opposite range first')
    const lv = parseFloat(level)
    if (!(lv > 0)) return setErr("Type the level's price (the line you watch)")
    setBusy(true); setRes(null); setDone(false)
    const r = await api('/api/quick-bt/auto', { method: 'POST', body: JSON.stringify({ pair: draft.pair, side: draft.side,
      level: lv, mode, tol_pips: parseFloat(tol) || 0, keys: Object.keys(draft.results).length ? Object.keys(draft.results) : null, start: zonedIso(draft.date, '00:00', timezone || 'UTC'),
      save: true, date: draft.date, range_type: draft.range_type, valid: draft.valid, note: draft.note }) })
    setBusy(false)
    const j = await r.json().catch(() => ({}))
    if (!r.ok) return setErr(j.detail || 'Auto-check failed')
    setRes(j)
    setLevel('')
    onSaved(j)
  }
  const labelOf = (k: string) => LABEL[k] || k
  const col = (o: string) => o === 'win' ? 'var(--bullish)' : o === 'loss' ? 'var(--bearish)' : '#eab308'
  return (
    <div style={{ border: '1px dashed var(--accent)', borderRadius: 10, padding: 12, marginBottom: 12, background: 'var(--surface)' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        <b style={{ fontSize: 13.5, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)' }}><Wand2 size={15} color="var(--accent)" /> Auto-check</b>
        <input value={level} onChange={e => setLevel(e.target.value)} placeholder="Level price" inputMode="decimal" style={{ ...field, width: 120 }} aria-label="The level line's price" />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: 4 }}
          title="A wick this close to your line counts as reaching it (your chart's prices and this data differ by fractions of a pip)">
          within <input value={tol} onChange={e => setTol(e.target.value)} inputMode="decimal" style={{ ...field, width: 46, padding: '6px 6px' }} aria-label="Tolerance in pips" /> pip</span>
        <span style={{ display: 'inline-flex', gap: 4 }}>
          <button type="button" style={{ ...pill(mode === 'limit'), padding: '5px 10px' }} onClick={() => setMode('limit')} title="Limit at the OC / CISD line / PCL open / covered candle's open">Limit</button>
          <button type="button" style={{ ...pill(mode === 'instant'), padding: '5px 10px' }} onClick={() => setMode('instant')} title="At the confirmation candle's close">Instant</button>
        </span>
        <button onClick={go} disabled={busy} style={{ ...pill(true), display: 'flex', alignItems: 'center', gap: 6 }}>
          {busy ? <Loader2 size={14} className="spin" /> : <Wand2 size={14} />} {busy ? 'Checking…' : 'Check and save'}
        </button>
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 6 }}>
        The date is only where the search starts: after each check it moves by itself to the day the ★ first trade triggered (and the setup is saved under that day), so you only change it when you jump ahead. Type the level you watch (an OC: the first candle&apos;s close; a V: its level). Watching starts by itself once a whole H4 candle has moved away from your level. It checks only the confirmations you tick below (none ticked = all of them), finds each one whose wick reaches the line and trades it at TP 3R / BE 2R with your retakes. ★ first is the trade you&apos;d really take; the others keep being checked after its TP (marked &quot;after TP&quot;) until an H4 candle closes beyond the line, so each confirmation gets its own win rate.
        {cov && cov.pct < 100 && <> · Data downloaded so far: <b>{cov.pct}%</b>{cov.next_missing ? ` (up to ${isoToDmy(cov.next_missing)})` : ''}</>}
      </div>
      {err && <div style={{ color: 'var(--bearish)', fontSize: 12.5, fontWeight: 600, marginTop: 6 }}>{err}</div>}
      {res && (
        <div style={{ marginTop: 10, fontSize: 12.5, color: 'var(--text-secondary)' }}>
          <div style={{ marginBottom: 6 }}>
            {res.armed_at && <>Watching began <b>{when(res.armed_at)}</b> (the first whole H4 candle away from your level). </>}
            {res.first_tp_at && <>★ first reached its TP <b>{when(res.first_tp_at)}</b>. </>}
            Setup ended <b>{when(res.setup_end || res.watched_until)}</b>{res.end_reason ? ` (${res.end_reason})` : ''}.
            {' '}{Object.keys(res.results).length ? 'Saved with its pictures, marked "to review".' : 'No confirmation reached the level (saved as a setup with none).'}
          </div>
          {Object.entries(res.results).map(([k, v]) => (
            <div key={k} style={{ marginBottom: 4 }}>
              <b style={{ color: 'var(--text-primary)' }}>{labelOf(k)}</b>{res.first === k ? ' ★' : ''}{v.after_tp ? ' (after TP)' : ''}:{' '}
              {v.trades.map((t, i) => (
                <span key={i}>{i ? ' → ' : ''}{when(t.time)} {t.limit ? `limit ${t.entry}${t.filled ? ` (filled ${when(t.filled)})` : ''}` : `entry ${t.entry}`} SL {t.sl} TP {t.tp}{' '}
                  <b style={{ color: col(t.outcome) }}>{t.outcome.toUpperCase()}</b>{t.exit ? ` (${when(t.exit)})` : ''}
                  {t.exit && <b style={{ color: 'var(--text-primary)' }}>{` · held ${heldFor(t.filled || t.time, t.exit)}`}</b>}</span>
              ))}
            </div>
          ))}
          {res.saved_id && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', margin: '10px 0 4px' }}>
              <button onClick={() => onRead(res.saved_id!)} style={{ ...pill(true), display: 'flex', alignItems: 'center', gap: 6 }}>
                <BookOpen size={14} /> Review it now (pictures)</button>
              {done
                ? <span style={{ color: 'var(--bullish)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}><Check size={14} /> Reviewed</span>
                : <button onClick={async () => { await onReviewed(res.saved_id!); setDone(true) }} style={{ ...pill(false, 'var(--bullish)'), display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Check size={14} /> Looks right: reviewed</button>}
            </div>
          )}
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>{res.note}</div>
        </div>
      )}
    </div>
  )
}

function blank(): Draft {
  let last: Partial<Draft> = {}
  try { last = JSON.parse(localStorage.getItem(LAST_KEY) || '{}') } catch { /* private mode */ }
  return { pair: last.pair || 'EURUSD', date: last.date || '2020-01-01', side: '', range_type: last.range_type || '',
    valid: true, results: {}, first: null, note: '' }
}

const card: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 16 }
const pill = (on: boolean, color = 'var(--accent)'): React.CSSProperties => ({
  padding: '7px 13px', borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: 'pointer',
  border: `1px solid ${on ? color : 'var(--border)'}`, background: on ? color : 'transparent',
  color: on ? 'white' : 'var(--text-secondary)',
})
const field: React.CSSProperties = {
  padding: '8px 10px', borderRadius: 8, fontSize: 13, border: '1px solid var(--border)', background: 'var(--bg)',
  color: 'var(--text-primary)', outline: 'none',
}

export default function QuickBacktest({ tabs }: { tabs?: React.ReactNode }) {
  const [allSetups, setSetups] = useState<Setup[]>([])
  // One journal per timeframe (user, 2026-11-25): H1, M15 and M5 entries each read on their own; All = every one
  const [journal, setJournal] = useState<Journal>('all')
  useEffect(() => { try { const j = localStorage.getItem('mbp_qbt_journal'); if (j && JOURNALS.some(x => x[0] === j)) setJournal(j as Journal) } catch { /* private mode */ } }, [])
  const pickJournal = (j: Journal) => { setJournal(j); try { localStorage.setItem('mbp_qbt_journal', j) } catch { /* private mode */ } }
  const setups = useMemo(() => inJournal(allSetups, journal), [allSetups, journal])
  const orig = (s: Setup) => allSetups.find(x => x.id === s.id) ?? s
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<Draft>(() => blank())
  const [editId, setEditId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [rangeF, setRangeF] = useState<'all' | 'inside' | 'opposite'>('all')
  const [yearF, setYearF] = useState('all')
  const [showAll, setShowAll] = useState(false)
  const [reviewOnly, setReviewOnly] = useState(false)
  // the Setups section opens and closes (user, 2026-11-24); her choice is remembered on this browser
  const [setupsOpen, setSetupsOpen] = useState(true)
  const [picked, setPicked] = useState<Set<number>>(new Set())   // ticked setups, for Delete selected
  const pick = (id: number) => setPicked(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const deleteMany = async (all: boolean) => {
    const n = all ? allSetups.length : picked.size
    if (!n) return
    if (!confirm(all ? `Delete ALL ${n} setups and their pictures? This can't be undone.` : `Delete the ${n} ticked setup${n === 1 ? '' : 's'} and their pictures? This can't be undone.`)) return
    if (all && prompt('Type DELETE to confirm deleting every setup') !== 'DELETE') return
    await api('/api/quick-bt/delete', { method: 'POST', body: JSON.stringify(all ? { all: true, confirm: 'DELETE' } : { ids: [...picked] }) })
    setPicked(new Set())
    load()
  }
  useEffect(() => { try { if (localStorage.getItem('mbp_qbt_setups') === 'closed') setSetupsOpen(false) } catch { /* private mode */ } }, [])
  const toggleSetups = () => setSetupsOpen(o => {
    try { localStorage.setItem('mbp_qbt_setups', o ? 'closed' : 'open') } catch { /* private mode */ }
    return !o
  })
  const pendingN = setups.filter(s => s.auto && !s.reviewed).length
  const reviewView = reviewOnly && pendingN > 0
  const [gallery, setGallery] = useState<Setup | null>(null)
  const [reading, setReading] = useState<Setup | null>(null)
  const [openId, setOpenId] = useState<number | null>(null)   // open this setup's page once the list has it

  const load = useCallback(async () => {
    const r = await api('/api/quick-bt')
    if (r.ok) setSetups((await r.json()).setups)
    setLoading(false)
  }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (openId == null) return
    const s = allSetups.find(x => x.id === openId)
    if (s) { setReading(s); setOpenId(null) }
  }, [openId, allSetups])

  // ---- form
  const formed = Object.keys(draft.results)
  const setRes = (k: string, patch: Partial<Res> | null) => setDraft(d => {
    const results = { ...d.results }
    if (patch === null) delete results[k]
    else {
      const prev = results[k] as Res | undefined
      results[k] = { outcome: prev?.outcome ?? '', takes: prev?.takes ?? 1, ...patch }
    }
    const keys = Object.keys(results)
    let first = d.first && results[d.first] ? d.first : null
    if (!first && keys.length === 1) first = keys[0]
    return { ...d, results, first }
  })
  const save = async () => {
    if (!draft.date) return setMsg('Pick the date')
    if (!draft.side) return setMsg('Pick Buy or Sell')
    if (!draft.range_type) return setMsg('Pick Inside range or Opposite range')
    const noResult = formed.find(k => !draft.results[k].outcome)
    if (noResult) return setMsg(`Pick Win, BE or Loss for ${LABEL[noResult]}`)
    if (formed.length > 1 && !draft.first) return setMsg('Star the confirmation that formed first')
    setSaving(true); setMsg('')
    const r = await api(editId ? `/api/quick-bt/${editId}` : '/api/quick-bt',
      { method: editId ? 'PUT' : 'POST', body: JSON.stringify(draft) })
    setSaving(false)
    if (!r.ok) { setMsg((await r.json().catch(() => ({}))).detail || 'Could not save'); return }
    try { localStorage.setItem(LAST_KEY, JSON.stringify({ pair: draft.pair, date: draft.date, range_type: draft.range_type })) } catch { /* private mode */ }
    setMsg(editId ? 'Updated ✓' : 'Saved ✓ Next setup')
    setEditId(null)
    setDraft(blank())
    load()
  }
  const edit = (shown: Setup) => {
    const s = orig(shown)      // the whole setup, every timeframe's results
    setEditId(s.id)
    setDraft({ pair: s.pair, date: s.date, side: s.side, range_type: s.range_type, valid: s.valid,
      results: s.results, first: s.first, note: s.note })
    setMsg(`Editing the setup of ${fmtDay(s.date)}`)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const remove = async (s: Setup) => {
    if (!confirm(`Delete the ${s.side} setup of ${fmtDay(s.date)}?`)) return
    await api(`/api/quick-bt/${s.id}`, { method: 'DELETE' })
    load()
  }

  // ---- results
  const years = useMemo(() => Array.from(new Set(setups.map(s => s.date.slice(0, 4)))).sort(), [setups])
  const shown = useMemo(() => setups.filter(s => s.valid && (rangeF === 'all' || s.range_type === rangeF)
    && (yearF === 'all' || s.date.startsWith(yearF))), [setups, rangeF, yearF])
  const stats = useMemo(() => {
    const rows = CONFS.map(([k, label]) => {
      const rs = shown.filter(s => s.results[k]).map(s => ({ r: s.results[k], tp: s.tp_r }))
      return row(label, rs)
    })
    const firstRs = shown.filter(s => s.first && s.results[s.first]).map(s => ({ r: s.results[s.first as string], tp: s.tp_r }))
    return { rows, first: row('★ Always take the first to form', firstRs) }
  }, [shown])
  const best = stats.rows.filter(r => r.setups > 0).sort((a, b) => b.total - a.total)[0]
  const valid = setups.filter(s => s.valid)
  const reached = valid.length ? valid.map(s => s.date).sort().slice(-1)[0] : null

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <TopBar title="Quick Backtest" />
      <main style={{ flex: 1, width: '100%', padding: '20px 24px', maxWidth: 1100 }}>
        {tabs}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '4px 0 14px' }}>
          {JOURNALS.map(([j, name, holds]) => {
            const n = j === 'all' ? allSetups.length : inJournal(allSetups, j).length
            return (
              <button key={j} onClick={() => pickJournal(j)} style={{ ...pill(journal === j), display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 1, padding: '7px 13px', textAlign: 'left' }}>
                <span style={{ fontWeight: 800, fontSize: 13 }}>{name} <span style={{ opacity: 0.75, fontWeight: 600 }}>({n})</span></span>
                <span style={{ fontSize: 10.5, opacity: 0.8, fontWeight: 600 }}>{holds}</span>
              </button>
            )
          })}
        </div>
        <JournalBook title={JOURNALS.find(x => x[0] === journal)?.[1].replace(/^\S+\s/, '') ?? 'Journal'} journal={journal} setups={setups}
          onEdit={edit} onReviewed={async s => { await api(`/api/quick-bt/${s.id}/reviewed`, { method: 'POST' }); load() }} onChanged={load} />
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Zap size={20} color="var(--accent)" /> Quick Backtest
          </h1>
          <Fold id="intro" plain title={<span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)' }}>How this page works</span>}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>
            Only you see this. One pass through the years: at each setup, tick every confirmation (H1, M15 OCTGD, M15 CISD, M5 CISD) that formed at the
            POI and star the first one. TP 3R, breakeven at 2R. Every trade you place counts: takes before the last are
            losses, and Win % is wins out of all trades.
          </p>
          </Fold>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 16 }}>
          <Tile label="Setups logged" value={String(valid.length)} />
          <Tile label="Reached" value={reached ? fmtDay(reached) : '—'} />
          <Tile label="Best confirmation" value={best ? `${best.label.replace(/^H1 /, '')} ${fmtR(best.total)}` : '—'} />
        </div>

        {/* ---------- the form ---------- */}
        <div style={{ ...card, marginBottom: 18 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 12 }}>
            <DateDMY value={draft.date} onChange={v => setDraft(d => ({ ...d, date: v }))} />
            <input value={draft.pair} onChange={e => setDraft(d => ({ ...d, pair: e.target.value.toUpperCase() }))} style={{ ...field, width: 100 }} aria-label="Pair" />
            <button style={pill(draft.side === 'buy', 'var(--bullish)')} onClick={() => setDraft(d => ({ ...d, side: 'buy' }))}>Buy</button>
            <button style={pill(draft.side === 'sell', 'var(--bearish)')} onClick={() => setDraft(d => ({ ...d, side: 'sell' }))}>Sell</button>
            <span style={{ width: 8 }} />
            <button style={pill(draft.range_type === 'inside')} onClick={() => setDraft(d => ({ ...d, range_type: 'inside' }))}>Inside range</button>
            <button style={pill(draft.range_type === 'opposite')} onClick={() => setDraft(d => ({ ...d, range_type: 'opposite' }))}>Opposite range</button>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12, cursor: 'pointer' }}>
            <input type="checkbox" checked={draft.valid} onChange={e => setDraft(d => ({ ...d, valid: e.target.checked }))} style={{ width: 17, height: 17 }} />
            Setup valid: breakout ✓ · liquidity ✓ · POI ✓
            {!draft.valid && <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>(saved, not counted)</span>}
          </label>

          <AutoCheck draft={draft} onSaved={res => {
            try { localStorage.setItem(LAST_KEY, JSON.stringify({ pair: draft.pair, date: res.trigger_date || draft.date, range_type: draft.range_type })) } catch { /* private mode */ }
            setMsg(`Saved ✓ ${Object.keys(res.results).length} confirmation${Object.keys(res.results).length === 1 ? '' : 's'}, ${res.pictures ?? 0} picture${res.pictures === 1 ? '' : 's'} · marked to review. Next level.`)
            // keep her ticks for the next level: Auto-check checks only the ticked confirmations (2026-11-24)
            setDraft(d => ({ ...blank(), date: res.trigger_date || d.date, pair: d.pair, range_type: d.range_type, side: d.side,
              results: Object.fromEntries(Object.keys(d.results).map(k => [k, { outcome: '' as const, takes: 1 }])) }))
            load()
          }} onRead={id => { setOpenId(id); load() }}
            onReviewed={async id => { await api(`/api/quick-bt/${id}/reviewed`, { method: 'POST' }); load() }} />
          <TfPicker results={draft.results} onSet={(keys, on) => keys.forEach(k => {
            if (on && !draft.results[k]) setRes(k, {})
            if (!on && draft.results[k]) setRes(k, null)
          })} />
          <Fold id="byhand" plain force={!!editId} title={<span style={{ fontSize: 13.5 }}>Confirmations, results and note (to log by hand)</span>}
            summary={Object.keys(draft.results).length ? `${Object.keys(draft.results).length} ticked` : 'none ticked'}>
          <div style={{ display: 'grid', gap: 6 }}>
            {CONFS.map(([k, label]) => {
              const r = draft.results[k]
              return (
                <div key={k} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, padding: '6px 8px', borderRadius: 8,
                  background: r ? 'var(--surface)' : 'transparent', border: '1px solid var(--border)' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 7, width: 150, fontSize: 13.5, fontWeight: 700, color: r ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={!!r} onChange={e => setRes(k, e.target.checked ? {} : null)} style={{ width: 16, height: 16 }} />
                    {label}
                  </label>
                  {OUT.map(([o, ol, c]) => (
                    <button key={o} style={{ ...pill(r?.outcome === o, c), padding: '5px 11px' }} onClick={() => setRes(k, { outcome: o })}>{ol}</button>
                  ))}
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 6, fontSize: 12, color: 'var(--text-secondary)' }} title="How many times you took it before price closed outside the level">
                    takes
                    <button disabled={!r || r.takes <= 1} onClick={() => r && setRes(k, { takes: r.takes - 1 })} style={stepBtn} aria-label="Fewer takes"><Minus size={12} /></button>
                    <b style={{ minWidth: 14, textAlign: 'center', color: 'var(--text-primary)' }}>{r ? r.takes : '–'}</b>
                    <button disabled={!r} onClick={() => r && setRes(k, { takes: r.takes + 1 })} style={stepBtn} aria-label="More takes"><Plus size={12} /></button>
                  </span>
                  <button onClick={() => r && setDraft(d => ({ ...d, first: k }))} disabled={!r} title="Formed first: the one you would trade"
                    style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, border: 'none', background: 'none', cursor: r ? 'pointer' : 'default',
                      fontSize: 12, fontWeight: 700, color: draft.first === k ? '#eab308' : 'var(--text-muted)', opacity: r ? 1 : 0.35 }}>
                    <Star size={15} fill={draft.first === k ? '#eab308' : 'none'} /> first
                  </button>
                  {r?.outcome && <span style={{ fontSize: 12, fontWeight: 800, width: 48, textAlign: 'right', color: rOf(r, 3) > 0 ? 'var(--bullish)' : rOf(r, 3) < 0 ? 'var(--bearish)' : 'var(--text-secondary)' }}>{fmtR(rOf(r, 3))}</span>}
                </div>
              )
            })}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginTop: 12 }}>
            <input value={draft.note} onChange={e => setDraft(d => ({ ...d, note: e.target.value }))} placeholder="Note (optional)" style={{ ...field, flex: 1, minWidth: 180 }} />
            {editId && <button style={pill(false)} onClick={() => { setEditId(null); setDraft(blank()); setMsg('') }}>Cancel</button>}
            <button onClick={save} disabled={saving} style={{ ...pill(true), padding: '9px 22px', display: 'flex', alignItems: 'center', gap: 6 }}>
              {saving && <Loader2 size={14} className="spin" />} {editId ? 'Update setup' : 'Save setup'}
            </button>
          </div>
          </Fold>
          {msg && <div style={{ marginTop: 8, fontSize: 12.5, fontWeight: 600, color: msg.includes('✓') ? 'var(--bullish)' : msg.startsWith('Editing') ? 'var(--text-secondary)' : 'var(--bearish)' }}>{msg}</div>}
        </div>

        {/* ---------- results ---------- */}
        <Fold id="results" title={<><Trophy size={16} color="#eab308" /> Results ({shown.length} setup{shown.length === 1 ? '' : 's'})</>}
          summary={best ? `best: ${best.label} ${fmtR(best.total)} · ★ first ${fmtR(stats.first.total)}` : undefined}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ marginRight: 'auto' }} />
            {(['all', 'inside', 'opposite'] as const).map(f => (
              <button key={f} style={{ ...pill(rangeF === f), padding: '5px 11px', fontSize: 12 }} onClick={() => setRangeF(f)}>
                {f === 'all' ? 'All ranges' : f === 'inside' ? 'Inside' : 'Opposite'}
              </button>
            ))}
            <select value={yearF} onChange={e => setYearF(e.target.value)} style={{ ...field, padding: '5px 8px', fontSize: 12 }} aria-label="Year">
              <option value="all">All years</option>
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', fontSize: 11.5, textAlign: 'right' }}>
                  <th style={{ textAlign: 'left', padding: '6px 8px' }}>Confirmation</th>
                  <th style={th}>Setups</th><th style={th}>Trades</th><th style={th}>Win</th><th style={th}>BE</th>
                  <th style={th}>Loss</th><th style={th}>Win %</th><th style={th}>Total R</th><th style={th}>R / setup</th>
                </tr>
              </thead>
              <tbody>
                {[...stats.rows].sort((a, b) => b.total - a.total).map(r => <StatRow key={r.label} r={r} best={best?.label === r.label} />)}
                <StatRow r={stats.first} first />
              </tbody>
            </table>
          </div>
        </Fold>

        {/* ---------- monthly review (user, 2026-11-24) ---------- */}
        <Fold id="monthly" title={<><CalendarDays size={16} color="var(--accent)" /> Monthly review</>} summary="each month, as if you took each setup every time">
          <MonthlyReview setups={shown} bare />
        </Fold>

        {/* ---------- setups ---------- */}
        <div id="qbt-setups" style={card}>
          <button onClick={() => toggleSetups()} aria-expanded={setupsOpen}
            style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', background: 'none', border: 'none', padding: 0, cursor: 'pointer',
              marginBottom: setupsOpen ? 10 : 0, textAlign: 'left' }}>
            <ChevronDown size={16} color="var(--text-muted)" style={{ transition: 'transform 0.15s', transform: setupsOpen ? 'none' : 'rotate(-90deg)' }} />
            <h2 style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>Setups</h2>
            <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{setups.length}{pendingN ? ` · ${pendingN} to review` : ''}</span>
            <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>{setupsOpen ? 'Hide' : 'Show'}</span>
          </button>
          {!setupsOpen ? null : loading ? <Loader2 size={18} className="spin" /> : setups.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No setups yet. Start at January 2020 and save your first one above.</p>
          ) : (
            <div style={{ display: 'grid', gap: 6 }}>
              {/* the filter switches itself off once nothing is left to review, so the full list never goes blank */}
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12.5, flexWrap: 'wrap' }}>
                <button style={pill(!reviewView)} onClick={() => setReviewOnly(false)}>All setups ({setups.length})</button>
                {pendingN > 0 && <button style={pill(reviewView, '#eab308')} onClick={() => setReviewOnly(true)}>To review ({pendingN})</button>}
                <span style={{ color: 'var(--text-muted)' }}>{pendingN > 0 ? 'Auto-checked setups wait in "To review" until you tick ✓; reviewed ones stay in All setups.' : 'Click 📖 on a setup to read it like a diary page.'}</span>
                <span style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
                  {!reviewView && (
                    <label style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                      <input type="checkbox" checked={picked.size > 0 && picked.size === setups.length}
                        onChange={e => setPicked(e.target.checked ? new Set(setups.map(x => x.id)) : new Set())} /> Tick all</label>
                  )}
                  {picked.size > 0 && <button onClick={() => deleteMany(false)} style={{ ...pill(false, 'var(--bearish)'), padding: '5px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, color: 'var(--bearish)', borderColor: 'var(--bearish)' }}>
                    <Trash2 size={12} /> Delete selected ({picked.size})</button>}
                  <button onClick={() => deleteMany(true)} style={{ ...pill(false), padding: '5px 10px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, color: 'var(--bearish)' }}>
                    <Trash2 size={12} /> Delete all</button>
                </span>
              </div>
              {reviewView && setups.filter(s => s.auto && !s.reviewed).map(s => (
                <div key={`rv${s.id}`} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, display: 'grid', gap: 10 }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                    <b style={{ fontSize: 15, color: 'var(--text-primary)' }}>{setupTitle(s)}</b>
                    {CONFS.filter(([k]) => s.results[k]).map(([k]) => {
                      const r = s.results[k]
                      const c = OUT.find(o => o[0] === r.outcome)?.[2] ?? 'var(--text-muted)'
                      return <span key={k} style={{ padding: '2px 7px', borderRadius: 6, fontSize: 12, fontWeight: 700, border: `1px solid ${c}`, color: c }}>
                        {s.first === k && '★ '}{SHORT[k]} {r.outcome === 'win' ? 'W' : r.outcome === 'be' ? 'BE' : 'L'}{r.takes > 1 ? ` ×${r.takes}` : ''}{r.after_tp ? ' · after TP' : ''}</span>
                    })}
                  </div>
                  <SetupPictures setup={s} />
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={async () => { await api(`/api/quick-bt/${s.id}/reviewed`, { method: 'POST' }); load() }}
                      style={{ ...pill(true, 'var(--bullish)'), display: 'flex', alignItems: 'center', gap: 5 }}><Check size={14} /> Looks right: reviewed</button>
                    <button onClick={() => edit(s)} style={{ ...pill(false), display: 'flex', alignItems: 'center', gap: 5 }}><Pencil size={13} /> Correct it</button>
                    <button onClick={() => remove(s)} style={{ ...pill(false), display: 'flex', alignItems: 'center', gap: 5 }}><Trash2 size={13} /> Delete</button>
                  </div>
                </div>
              ))}
              {!reviewView && (showAll ? setups : setups.slice(0, 40)).map(s => (
                <div key={s.id} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontSize: 12.5, padding: '7px 9px',
                  borderRadius: 8, border: '1px solid var(--border)', opacity: s.valid ? 1 : 0.55 }}>
                  <input type="checkbox" checked={picked.has(s.id)} onChange={() => pick(s.id)} aria-label={`Tick the setup of ${fmtDay(s.date)}`} style={{ width: 16, height: 16, cursor: 'pointer' }} />
                  <button onClick={() => setReading(s)} style={{ ...iconBtn, color: 'var(--accent)' }} aria-label="Read this setup" title="Read it like a diary page"><BookOpen size={14} /></button>
                  <b style={{ width: 92, color: 'var(--text-primary)' }}>{fmtDay(s.date)}</b>
                  <span style={{ fontWeight: 800, color: s.side === 'buy' ? 'var(--bullish)' : 'var(--bearish)', width: 34 }}>{s.side.toUpperCase()}</span>
                  <span style={{ color: 'var(--text-secondary)', width: 62 }}>{s.range_type === 'inside' ? 'Inside' : 'Opposite'}</span>
                  {Object.keys(s.results).length === 0 && <span style={{ color: 'var(--text-muted)' }}>no confirmation formed</span>}
                  {CONFS.filter(([k]) => s.results[k]).map(([k]) => {
                    const r = s.results[k]
                    const c = OUT.find(o => o[0] === r.outcome)?.[2] ?? 'var(--text-muted)'
                    return (
                      <span key={k} style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 700, border: `1px solid ${c}`, color: c,
                        background: s.first === k ? 'color-mix(in srgb, #eab308 15%, transparent)' : 'transparent' }}>
                        {s.first === k && '★ '}{SHORT[k]} {r.outcome === 'win' ? 'W' : r.outcome === 'be' ? 'BE' : 'L'}{r.takes > 1 ? ` ×${r.takes}` : ''}{r.after_tp ? ' · after TP' : ''}
                      </span>
                    )
                  })}
                  {!s.valid && <span style={{ color: 'var(--text-muted)' }}>(not counted)</span>}
                  {s.note && <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{s.note}</span>}
                  {s.auto && !s.reviewed && <span style={{ fontSize: 11, fontWeight: 800, color: '#eab308', border: '1px solid #eab308', borderRadius: 6, padding: '1px 6px' }}>to review</span>}
                  <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                    {!!s.pictures && <button onClick={() => setGallery(s)} style={{ ...iconBtn, width: 'auto', padding: '0 7px', gap: 4, display: 'flex', alignItems: 'center' }} aria-label="Pictures"><Camera size={13} /> {s.pictures}</button>}
                    {s.auto && !s.reviewed && <button onClick={async () => { await api(`/api/quick-bt/${s.id}/reviewed`, { method: 'POST' }); load() }} style={iconBtn} aria-label="Mark reviewed" title="Looked at it: mark reviewed"><Check size={13} /></button>}
                    <button onClick={() => edit(s)} style={iconBtn} aria-label="Edit"><Pencil size={13} /></button>
                    <button onClick={() => remove(s)} style={iconBtn} aria-label="Delete"><Trash2 size={13} /></button>
                  </span>
                </div>
              ))}
              {!showAll && setups.length > 40 && (
                <button onClick={() => setShowAll(true)} style={{ ...pill(false), justifySelf: 'start' }}>Show all {setups.length}</button>
              )}
              <CloseBar label="Close setups" onClose={() => { toggleSetups(); document.getElementById('qbt-setups')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }} />
            </div>
          )}
        </div>
        {reading && <SetupBook setup={reading} onClose={() => setReading(null)} onEdit={() => { const s = reading; setReading(null); edit(s) }}
          onReviewed={async () => { await api(`/api/quick-bt/${reading.id}/reviewed`, { method: 'POST' }); setReading(null); load() }} />}
        {gallery && <Gallery setup={gallery} onClose={() => setGallery(null)}
          onReviewed={async () => { await api(`/api/quick-bt/${gallery.id}/reviewed`, { method: 'POST' }); setGallery(null); load() }} />}
      </main>
    </div>
  )
}

// ---- The three journals (user, 2026-11-25): each shows only its timeframe's entries, with its own ★ first
type Journal = 'all' | 'H1' | 'M15' | 'M5'
const JOURNALS: [Journal, string, string][] = [
  ['all', '📚 All entries', 'every confirmation'],
  ['H1', '🕐 H1 journal', 'PCL · Engulfing · OCTGD 1 · OCTGD 2 · H1 CISD'],
  ['M15', '🕒 M15 journal', 'M15 OCTGD · M15 OCTGD 2 · M15 CISD'],
  ['M5', '🕔 M5 journal', 'M5 CISD'],
]
// a setup as one journal sees it: only that timeframe's results; ★ first = the earliest of those to enter
// (saved entry times; for a hand-logged setup: its own ★ if it is in this journal, or the only one)
function inJournal(list: Setup[], j: Journal): Setup[] {
  if (j === 'all') return list
  const keys = TF_GROUPS.find(g => g[0] === j)?.[1] ?? []
  return list.flatMap(s => {
    const results = Object.fromEntries(Object.entries(s.results).filter(([k]) => keys.includes(k)))
    const ks = Object.keys(results)
    if (!ks.length) return []
    const timed = ks.filter(k => results[k].entered).sort((a, b) => results[a].entered!.localeCompare(results[b].entered!))
    const first = s.first && ks.includes(s.first) ? s.first : timed[0] ?? (ks.length === 1 ? ks[0] : null)
    return [{ ...s, results, first }]
  })
}

// Tick a whole timeframe's confirmations at once (user, 2026-11-24): a small dropdown of H1 / M15 / M5
const TF_GROUPS: [string, string[]][] = [
  ['H1', ['pcl', 'eng', 'octgd1', 'octgd2', 'cisd']],
  ['M15', ['octgd15', 'octgd215', 'cisd15']],
  ['M5', ['cisd5']],
]
function TfPicker({ results, onSet }: { results: Record<string, Res>; onSet: (keys: string[], on: boolean) => void }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])
  const state = (keys: string[]) => { const n = keys.filter(k => results[k]).length; return n === keys.length ? 'all' : n ? 'some' : 'none' }
  const chosen = TF_GROUPS.filter(([, ks]) => state(ks) === 'all').map(([tf]) => tf)
  return (
    <div ref={box} style={{ marginBottom: 8 }}>
      <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
        style={{ ...pill(chosen.length > 0), display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', fontSize: 12.5 }}>
        <Check size={13} /> Tick timeframes{chosen.length ? `: ${chosen.join(', ')}` : ''}
        <ChevronDown size={13} style={{ transition: 'transform 0.15s', transform: open ? 'rotate(180deg)' : 'none' }} />
      </button>
      {open && (
        // opens in the page's flow, pushing the rows down, so it never hides the rows it ticks (user, 2026-11-24)
        <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 4, background: 'var(--card)',
          border: '1px solid var(--border)', borderRadius: 10, padding: 6 }}>
          {TF_GROUPS.map(([tf, ks]) => {
            const st = state(ks)
            return (
              <label key={tf} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px', borderRadius: 7, cursor: 'pointer',
                fontSize: 13, color: 'var(--text-primary)' }}>
                <input type="checkbox" checked={st === 'all'} ref={el => { if (el) el.indeterminate = st === 'some' }}
                  onChange={e => onSet(ks, e.target.checked)} style={{ width: 16, height: 16 }} />
                <b>{tf}</b>
                <span style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>{ks.map(k => SHORT[k] || k).join(' · ')}</span>
              </label>
            )
          })}
          <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', paddingLeft: 6 }}>
            <button type="button" onClick={() => onSet(TF_GROUPS.flatMap(([, ks]) => ks), true)} style={{ ...pill(false), padding: '4px 10px', fontSize: 12 }}>All</button>
            <button type="button" onClick={() => onSet(TF_GROUPS.flatMap(([, ks]) => ks), false)} style={{ ...pill(false), padding: '4px 10px', fontSize: 12 }}>Clear</button>
          </div>
        </div>
      )}
    </div>
  )
}

// A setup read back as a page of the diary (user, 2026-11-24: "read the information like a book")
function SetupBook({ setup, onClose, onEdit, onReviewed, inline, onDelete }: { setup: Setup; onClose: () => void; onEdit: () => void; onReviewed: () => void; inline?: boolean; onDelete?: () => void }) {
  const { user } = useAuth()
  const [pics, setPics] = useState<{ id: number; conf: string; label: string; url: string }[] | null>(null)
  useEffect(() => {
    let gone = false
    const made: string[] = []
    ;(async () => {
      if (!setup.pictures) { setPics([]); return }
      const r = await api(`/api/quick-bt/${setup.id}/pictures`)
      const list: { id: number; conf: string; label: string }[] = r.ok ? (await r.json()).pictures : []
      const out = []
      for (const p of list) {
        const b = await api(`/api/quick-bt/picture/${p.id}`)
        if (!b.ok) continue
        const url = URL.createObjectURL(await b.blob())
        made.push(url)
        out.push({ ...p, url })
      }
      if (!gone) setPics(out)
    })()
    return () => { gone = true; made.forEach(u => URL.revokeObjectURL(u)) }
  }, [setup.id, setup.pictures])
  useEffect(() => {
    if (inline) return
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose, inline])
  const note = setup.note && !setup.note.startsWith('Auto-checked') ? setup.note.trim() : ''
  // ★ first reads first, then the rest in the page's usual order
  const keys = CONFS.map(([k]) => k).filter(k => setup.results[k] && setup.results[k].outcome)
    .sort((a, b) => (a === setup.first ? -1 : b === setup.first ? 1 : 0))
  const story = buildStory({
    id: setup.id, name: user?.name, date: setup.date, pair: setup.pair, direction: setup.side, hasNote: !!note,
    rows: keys.map(k => {
      const r = setup.results[k]
      return { slot: k, label: `${LABEL[k] || k}${setup.first === k ? ' (my ★ first)' : ''}${r.after_tp ? ' (after the first TP)' : ''}`,
        outcome: r.outcome as 'win' | 'loss' | 'be', rr: r.outcome === 'win' ? setup.tp_r : null, takes: r.takes, net: rOf(r, setup.tp_r) }
    }),
  })
  const setupLine = `It was ${setup.range_type === 'inside' ? 'an inside' : 'an opposite'} range setup${setup.level ? `, and my level was ${setup.level}` : ''}. `
    + (setup.valid ? 'The breakout, the liquidity and the POI were all there ✅' : "It didn't count as a valid setup, so it stays out of my numbers.")
  let n = 0
  const line = () => ({ animationDelay: `${(n++) * 0.14}s` })
  const picsOf = (k: string) => (pics || []).filter(p => p.conf === k)
  const page = (
        <div className="dp-wrap" style={{ borderTop: 'none' }}>
          <div className={`dp-page dp-${story.mood}`}>
            {story.sparks.map((e, i) => <span key={i} className={`dp-spark dp-spark${i}`} aria-hidden>{e}</span>)}
            <div className="dp-head dp-line" style={line()}>
              <span className="dp-ribbon">{story.ribbon}</span>
              <span className="dp-stamp">Backtest · {setup.pair} · {fmtDay(setup.date)}{setup.auto ? ' · auto-checked' : ''}</span>
            </div>
            <div className="diary-script dp-greet dp-line" style={line()}>{story.greeting}</div>
            <p className="dp-p dp-line" style={line()}>{story.opening}{story.noNote ? ` ${story.noNote}` : ''}</p>
            {note && <div className="dp-note dp-line" style={line()}>{note}</div>}
            <p className="dp-p dp-line" style={line()}>{setupLine}</p>
            {!keys.length && <p className="dp-p dp-line" style={line()}>No confirmation formed at my level this time 🌙 I watched, and I kept my peace.</p>}
            {story.rows.map(r => (
              <div key={r.slot} className="dp-line" style={line()}>
                <p className="dp-p">{r.text}{(() => {
                  const res = setup.results[r.slot]
                  if (!res?.entered) return null
                  const at = (iso: string) => new Date(iso).toLocaleString('en-GB', { timeZone: 'Africa/Lagos', weekday: 'short', day: 'numeric', month: 'short',
                    hour: 'numeric', minute: '2-digit', hour12: true }).replace(' am', 'am').replace(' pm', 'pm')
                  const end = res.outcome === 'win' ? 'it hit TP' : res.outcome === 'loss' ? 'the stop was hit' : 'it closed at breakeven'
                  return res.exit ? ` It triggered on ${at(res.entered)} and ${end} on ${at(res.exit)}: I held it for ${heldFor(res.entered, res.exit)} ⏳`
                    : ` It triggered on ${at(res.entered)} ⏳`
                })()}</p>
                {pics === null && setup.pictures ? <Loader2 size={16} className="spin" /> : picsOf(r.slot).map(p => (
                  <figure key={p.id} style={{ margin: '0 0 14px' }}>
                    <img src={p.url} alt={p.label} style={{ width: '100%', borderRadius: 10, display: 'block' }} />
                  </figure>
                ))}
              </div>
            ))}
            <div className="dp-foot dp-line" style={line()}>
              <div>
                <div className="dp-yours">{story.yours}</div>
                <div className="diary-script dp-sign">{story.signature}</div>
              </div>
              <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {setup.auto && !setup.reviewed && <button onClick={onReviewed} style={{ ...pill(true, 'var(--bullish)'), display: 'flex', alignItems: 'center', gap: 5 }}><Check size={13} /> Looks right: reviewed</button>}
                <button onClick={onEdit} style={{ ...pill(false), display: 'flex', alignItems: 'center', gap: 5 }}><Pencil size={12} /> Edit this page</button>
                {onDelete && <button onClick={onDelete} style={{ ...pill(false), display: 'flex', alignItems: 'center', gap: 5, color: 'var(--bearish)' }}><Trash2 size={12} /> Delete</button>}
              </span>
            </div>
          </div>
        </div>
  )
  if (inline) return page
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 400, background: 'rgba(0,0,0,0.85)', overflowY: 'auto', padding: 16 }}>
      <div onClick={e => e.stopPropagation()} className="fairy-diary dp-purple" style={{ maxWidth: 900, margin: '0 auto', background: 'var(--card)', borderRadius: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '10px 10px 0' }}>
          <button onClick={onClose} style={iconBtn} aria-label="Close"><X size={15} /></button>
        </div>
        {page}
      </div>
    </div>
  )
}

// A section that folds away (user, 2026-11-25: "the page is too busy"). Closed until she opens it; remembered on
// this browser. Open, it ends with a Close button that folds it and brings her back to its heading.
function useFold(id: string, start = false): [boolean, (v: boolean) => void] {
  const [open, setOpen] = useState(start)
  useEffect(() => { try { const v = localStorage.getItem(`mbp_qbt_fold_${id}`); if (v) setOpen(v === '1') } catch { /* private mode */ } }, [id])
  const set = (v: boolean) => { setOpen(v); try { localStorage.setItem(`mbp_qbt_fold_${id}`, v ? '1' : '0') } catch { /* private mode */ } }
  return [open, set]
}
function CloseBar({ onClose, label = 'Close' }: { onClose: () => void; label?: string }) {
  return (
    <button onClick={onClose} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, width: '100%', marginTop: 10,
      padding: '7px 10px', borderRadius: 8, border: '1px dashed var(--border)', background: 'transparent', color: 'var(--text-secondary)',
      cursor: 'pointer', fontSize: 12.5, fontWeight: 700 }}>
      <ChevronDown size={14} style={{ transform: 'rotate(180deg)' }} /> {label}
    </button>
  )
}
function Fold({ id, title, summary, children, force, start = false, plain }: { id: string; title: React.ReactNode; summary?: React.ReactNode
  children: React.ReactNode; force?: boolean; start?: boolean; plain?: boolean }) {
  const [open, setOpen] = useFold(id, start)
  const ref = useRef<HTMLDivElement>(null)
  const shown = open || !!force
  const close = () => { setOpen(false); ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }
  return (
    <div ref={ref} style={plain ? { marginBottom: 12 } : { ...card, marginBottom: 18 }}>
      <button onClick={() => (shown ? close() : setOpen(true))} aria-expanded={shown}
        style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', width: '100%', background: 'none', border: 'none', padding: 0,
          cursor: 'pointer', textAlign: 'left', color: 'var(--text-primary)', marginBottom: shown ? 12 : 0 }}>
        <ChevronDown size={16} color="var(--text-muted)" style={{ transition: 'transform 0.15s', transform: shown ? 'none' : 'rotate(-90deg)', flexShrink: 0 }} />
        <span style={{ fontSize: 15, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 6 }}>{title}</span>
        {summary && <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{summary}</span>}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>{shown ? 'Hide' : 'Show'}</span>
      </button>
      {shown && <>{children}<CloseBar onClose={close} /></>}
    </div>
  )
}

// A journal opened from its tab (user, 2026-11-25): months → the days with setups → that day's diary pages.
// Pages (and their pictures) load only when she opens a day.
const MONTHS_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
function JournalBook({ title, journal, setups, onEdit, onReviewed, onChanged }: { title: string; journal: Journal; setups: Setup[]
  onEdit: (s: Setup) => void; onReviewed: (s: Setup) => void; onChanged: () => void }) {
  // delete from this journal (owner, 2026-11-25): All entries = whole setups; H1 / M15 / M5 = only that journal's results
  const [selecting, setSelecting] = useState(false)
  const [picked, setPicked] = useState<Set<number>>(new Set())
  const pick = (id: number) => setPicked(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const keys = TF_GROUPS.find(g => g[0] === journal)?.[1] ?? []
  const remove = async (ids: number[] | 'all') => {
    const n = ids === 'all' ? setups.length : ids.length
    if (!n) return
    const what = journal === 'all' ? `${n === 1 ? 'this setup' : `${n} setups`} (every timeframe, with the pictures)`
      : `the ${journal} results of ${n === 1 ? 'this setup' : `${n} setups`} (their other timeframes stay; a setup with nothing left is removed)`
    if (!confirm(`Delete ${what}? This can't be undone.`)) return
    if (ids === 'all' && prompt(`Type DELETE to clear the whole ${title}`) !== 'DELETE') return
    const body = journal === 'all'
      ? (ids === 'all' ? { all: true, confirm: 'DELETE' } : { ids })
      : (ids === 'all' ? { all: true, confirm: 'DELETE', keys } : { ids, keys })
    await api(journal === 'all' ? '/api/quick-bt/delete' : '/api/quick-bt/remove-keys', { method: 'POST', body: JSON.stringify(body) })
    setPicked(new Set()); setSelecting(false)
    onChanged()
  }
  const months = useMemo(() => {
    const m = new Map<string, Map<string, Setup[]>>()
    for (const s of [...setups].sort((a, b) => b.date.localeCompare(a.date) || a.id - b.id)) {
      const mk = s.date.slice(0, 7)
      if (!m.has(mk)) m.set(mk, new Map())
      const days = m.get(mk)!
      days.set(s.date, [...(days.get(s.date) || []), s])
    }
    return [...m.entries()]
  }, [setups])
  const [openM, setOpenM] = useState<Set<string>>(new Set())
  const [openD, setOpenD] = useState<Set<string>>(new Set())
  const [bookOpen, setBookOpen] = useFold('book', true)
  const back = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  useEffect(() => { if (months.length) setOpenM(new Set([months[0][0]])) }, [title, months.length])   // newest month open
  const flip = (set: Set<string>, k: string) => { const n = new Set(set); if (n.has(k)) n.delete(k); else n.add(k); return n }
  const rTotal = (list: Setup[]) => list.reduce((t, s) => t + (s.first && s.results[s.first] ? rOf(s.results[s.first], s.tp_r) : 0), 0)
  const head: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', width: '100%', background: 'none', border: 'none',
    cursor: 'pointer', textAlign: 'left', padding: 0, color: 'var(--text-primary)' }
  const chev = (open: boolean) => <ChevronDown size={15} color="var(--text-muted)" style={{ transition: 'transform 0.15s', transform: open ? 'none' : 'rotate(-90deg)', flexShrink: 0 }} />
  if (!setups.length) return <div style={{ ...card, marginBottom: 16, color: 'var(--text-muted)', fontSize: 13 }}>{title}: nothing logged here yet.</div>
  return (
    <div id="qbt-book" className="fairy-diary dp-purple" style={{ ...card, marginBottom: 16, display: 'grid', gap: 10 }}>
      <button onClick={() => setBookOpen(!bookOpen)} aria-expanded={bookOpen} style={{ ...head, gap: 8 }}>
        <ChevronDown size={16} color="var(--text-muted)" style={{ transition: 'transform 0.15s', transform: bookOpen ? 'none' : 'rotate(-90deg)' }} />
        <span className="diary-script" style={{ fontSize: 26, color: 'var(--accent-hover)' }}>{title}</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>{bookOpen ? 'Hide' : 'Show'}</span>
      </button>
      {bookOpen && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <button onClick={() => { setSelecting(v => !v); setPicked(new Set()) }} style={{ ...pill(selecting), padding: '5px 11px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}>
            <Check size={12} /> {selecting ? 'Done selecting' : 'Select'}</button>
          {selecting && <button onClick={() => setPicked(picked.size === setups.length ? new Set() : new Set(setups.map(x => x.id)))}
            style={{ ...pill(false), padding: '5px 11px', fontSize: 12 }}>{picked.size === setups.length ? 'Untick all' : 'Tick all'}</button>}
          {selecting && picked.size > 0 && <button onClick={() => remove([...picked])} style={{ ...pill(false), padding: '5px 11px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, color: 'var(--bearish)', borderColor: 'var(--bearish)' }}>
            <Trash2 size={12} /> Delete selected ({picked.size})</button>}
          <button onClick={() => remove('all')} style={{ ...pill(false), padding: '5px 11px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, color: 'var(--bearish)', marginLeft: 'auto' }}>
            <Trash2 size={12} /> Delete all</button>
        </div>
      )}
      {bookOpen && months.map(([mk, days]) => {
        const all = [...days.values()].flat()
        const mOpen = openM.has(mk)
        const tot = rTotal(all)
        return (
          <div key={mk} id={`qbt-m-${mk}`} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px', background: 'var(--surface)' }}>
            <button style={head} onClick={() => setOpenM(o => flip(o, mk))} aria-expanded={mOpen}>
              {chev(mOpen)}
              <span className="diary-script" style={{ fontSize: 22, color: 'var(--accent-hover)' }}>{MONTHS_FULL[+mk.slice(5, 7) - 1]} {mk.slice(0, 4)}</span>
              <span style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{all.length} setup{all.length === 1 ? '' : 's'} · {days.size} day{days.size === 1 ? '' : 's'}</span>
              <b style={{ marginLeft: 'auto', fontSize: 13, color: tot > 0 ? 'var(--bullish)' : tot < 0 ? 'var(--bearish)' : 'var(--text-secondary)' }}>★ {fmtR(tot)}</b>
            </button>
            {mOpen && (
              <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                {[...days.entries()].map(([day, list]) => {
                  const dOpen = openD.has(day)
                  const dt = rTotal(list)
                  return (
                    <div key={day} id={`qbt-d-${day}`} style={{ border: '1px dashed var(--border)', borderRadius: 10, padding: '8px 12px' }}>
                      {selecting && (
                        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
                          {list.map(s => (
                            <label key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                              <input type="checkbox" checked={picked.has(s.id)} onChange={() => pick(s.id)} style={{ width: 15, height: 15 }} />
                              {s.side.toUpperCase()} {s.pair}{s.level ? ` · ${s.level}` : ''}
                            </label>
                          ))}
                        </div>
                      )}
                      <button style={head} onClick={() => setOpenD(o => flip(o, day))} aria-expanded={dOpen}>
                        {chev(dOpen)}
                        <b style={{ fontSize: 14 }}>{fmtDay(day)}</b>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                          {list.map(s => `${s.side.toUpperCase()} ${s.pair}`).join(' · ')}
                          {' · '}{list.flatMap(s => Object.keys(s.results).map(k => SHORT[k] || k)).filter((v, i, a) => a.indexOf(v) === i).join(', ') || 'no confirmation'}
                        </span>
                        <b style={{ marginLeft: 'auto', fontSize: 12.5, color: dt > 0 ? 'var(--bullish)' : dt < 0 ? 'var(--bearish)' : 'var(--text-secondary)' }}>★ {fmtR(dt)}</b>
                      </button>
                      {dOpen && list.map(s => <SetupBook key={s.id} inline setup={s} onClose={() => {}} onEdit={() => onEdit(s)} onReviewed={() => onReviewed(s)}
                        onDelete={() => remove([s.id])} />)}
                      {dOpen && <CloseBar label={`Close ${fmtDay(day)}`} onClose={() => { setOpenD(o => flip(o, day)); back(`qbt-d-${day}`) }} />}
                    </div>
                  )
                })}
                <CloseBar label={`Close ${MONTHS_FULL[+mk.slice(5, 7) - 1]}`} onClose={() => { setOpenM(o => flip(o, mk)); back(`qbt-m-${mk}`) }} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

interface Stat { label: string; setups: number; takes: number; win: number; be: number; loss: number; total: number }

// The pictures of an auto-checked setup: one chart per trade (fetched with the login token, shown full width)
function SetupPictures({ setup }: { setup: Setup }) {
  const [pics, setPics] = useState<{ id: number; label: string; url: string }[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let gone = false
    const made: string[] = []
    ;(async () => {
      const r = await api(`/api/quick-bt/${setup.id}/pictures`)
      const list: { id: number; label: string }[] = r.ok ? (await r.json()).pictures : []
      const out = []
      for (const p of list) {
        const b = await api(`/api/quick-bt/picture/${p.id}`)
        if (!b.ok) continue
        const url = URL.createObjectURL(await b.blob())
        made.push(url)
        out.push({ ...p, url })
      }
      if (!gone) { setPics(out); setLoading(false) }
    })()
    return () => { gone = true; made.forEach(u => URL.revokeObjectURL(u)) }
  }, [setup.id])
  if (loading) return <Loader2 size={18} className="spin" />
  if (pics.length === 0) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No pictures for this setup (no confirmation reached the level, or it was logged by hand).</p>
  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {pics.map(p => (
        <figure key={p.id} style={{ margin: 0 }}>
          <figcaption style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 4 }}>{p.label}</figcaption>
          <img src={p.url} alt={p.label} style={{ width: '100%', borderRadius: 8, display: 'block' }} />
        </figure>
      ))}
    </div>
  )
}

const setupTitle = (s: Setup) => `${fmtDay(s.date)} · ${s.side.toUpperCase()} · ${s.range_type === 'inside' ? 'Inside' : 'Opposite'} range${s.level ? ` · level ${s.level}` : ''}`

function Gallery({ setup, onClose, onReviewed }: { setup: Setup; onClose: () => void; onReviewed: () => void }) {
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 400, background: 'rgba(0,0,0,0.85)', overflowY: 'auto', padding: 16 }}>
      <div onClick={e => e.stopPropagation()} style={{ maxWidth: 1000, margin: '0 auto', background: 'var(--card)', borderRadius: 12, padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <b style={{ color: 'var(--text-primary)' }}>{setupTitle(setup)}</b>
          {setup.auto && !setup.reviewed && <button onClick={onReviewed} style={{ ...pill(true, 'var(--bullish)'), display: 'flex', alignItems: 'center', gap: 5 }}><Check size={14} /> Looks right: reviewed</button>}
          <button onClick={onClose} style={{ ...iconBtn, marginLeft: 'auto' }} aria-label="Close"><X size={15} /></button>
        </div>
        <SetupPictures setup={setup} />
      </div>
    </div>
  )
}

function row(label: string, rs: { r: Res; tp: number }[]): Stat {
  const s: Stat = { label, setups: rs.length, takes: 0, win: 0, be: 0, loss: 0, total: 0 }
  for (const { r, tp } of rs) {
    if (!r.outcome) continue
    // every trade placed counts (user, 2026-11-21): takes before the last are losses, the last is the ticked result
    s.takes += r.takes
    s.loss += r.takes - 1
    s[r.outcome] += 1
    s.total += rOf(r, tp)
  }
  return s
}

function StatRow({ r, best, first }: { r: Stat; best?: boolean; first?: boolean }) {
  const pct = r.takes ? Math.round(100 * r.win / r.takes) : 0     // wins out of every trade placed
  return (
    <tr style={{ borderTop: '1px solid var(--border)', textAlign: 'right', fontWeight: best || first ? 800 : 500,
      background: best ? 'color-mix(in srgb, var(--bullish) 10%, transparent)' : undefined }}>
      <td style={{ textAlign: 'left', padding: '7px 8px', color: first ? '#eab308' : 'var(--text-primary)' }}>{r.label}{best ? ' 🏆' : ''}</td>
      <td style={td}>{r.setups}</td><td style={td}>{r.takes}</td><td style={td}>{r.win}</td><td style={td}>{r.be}</td>
      <td style={td}>{r.loss}</td><td style={td}>{r.setups ? `${pct}%` : '—'}</td>
      <td style={{ ...td, color: r.total > 0 ? 'var(--bullish)' : r.total < 0 ? 'var(--bearish)' : 'var(--text-secondary)' }}>{r.setups ? fmtR(r.total) : '—'}</td>
      <td style={td}>{r.setups ? fmtR(r.total / r.setups) : '—'}</td>
    </tr>
  )
}

// ---- Monthly review: each month folded shut; opened, every confirmation's month as if she took that one every time
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
type MonthRow = Stat & { bestW: number; bestL: number }
// every trade in date order: a result with n takes = n-1 stop-outs, then its ticked outcome. A BE ends both streaks.
function streaks(rs: { r: Res }[]): { bestW: number; bestL: number } {
  let w = 0, l = 0, bestW = 0, bestL = 0
  for (const { r } of rs) {
    if (!r.outcome) continue
    const seq: Outcome[] = [...Array(Math.max(0, r.takes - 1)).fill('loss'), r.outcome]
    for (const o of seq) {
      if (o === 'win') { w++; l = 0 } else if (o === 'loss') { l++; w = 0 } else { w = 0; l = 0 }
      bestW = Math.max(bestW, w); bestL = Math.max(bestL, l)
    }
  }
  return { bestW, bestL }
}
function MonthlyReview({ setups, bare }: { setups: Setup[]; bare?: boolean }) {
  const months = useMemo(() => {
    const byMonth = new Map<string, Setup[]>()
    for (const s of [...setups].sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id)) {
      const m = s.date.slice(0, 7)
      byMonth.set(m, [...(byMonth.get(m) || []), s])
    }
    return [...byMonth.entries()].sort((a, b) => b[0].localeCompare(a[0])).map(([m, list]) => {
      const mk = (label: string, rs: { r: Res; tp: number }[]): MonthRow => ({ ...row(label, rs), ...streaks(rs) })
      const rows = CONFS.map(([k, label]) => mk(label, list.filter(s => s.results[k]).map(s => ({ r: s.results[k], tp: s.tp_r }))))
        .filter(r => r.setups > 0).sort((a, b) => b.total - a.total)
      const first = mk('★ Always take the first to form', list.filter(s => s.first && s.results[s.first]).map(s => ({ r: s.results[s.first as string], tp: s.tp_r })))
      return { m, n: list.length, rows, first }
    })
  }, [setups])
  if (!months.length) return null
  const rc = (v: number) => v > 0 ? 'var(--bullish)' : v < 0 ? 'var(--bearish)' : 'var(--text-secondary)'
  const verdict = (v: number) => v > 0 ? 'Profit' : v < 0 ? 'Loss' : 'Flat'
  return (
    <div style={bare ? undefined : { ...card, marginBottom: 18 }}>
      {!bare && <h2 style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
        <CalendarDays size={16} color="var(--accent)" /> Monthly review
      </h2>}
      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 10px' }}>
        Each month as if you took that setup every time it formed. Streaks count every trade in date order (a stop-out before a retake is a loss; a breakeven ends a streak). Follows the range and year filters above.
      </p>
      <div style={{ display: 'grid', gap: 6 }}>
        {months.map(({ m, n, rows, first }) => (
          <details key={m} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: '8px 12px' }}>
            <summary style={{ cursor: 'pointer', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, fontSize: 13.5, listStyle: 'none' }}>
              <ChevronDown size={14} className="mr-chev" color="var(--text-muted)" />
              <b style={{ color: 'var(--text-primary)', minWidth: 130 }}>{MONTHS_LONG[+m.slice(5, 7) - 1]} {m.slice(0, 4)}</b>
              <span style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{n} setup{n === 1 ? '' : 's'}</span>
              <span style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>★ first: <b style={{ color: rc(first.total) }}>{fmtR(first.total)}</b></span>
              <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 800, padding: '2px 9px', borderRadius: 999, color: rc(first.total),
                border: `1px solid ${rc(first.total)}` }}>{verdict(first.total)}</span>
            </summary>
            <div style={{ overflowX: 'auto', marginTop: 8 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', fontSize: 11, textAlign: 'right' }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Setup taken every time</th>
                    <th style={th}>Setups</th><th style={th}>Trades</th><th style={th}>W / BE / L</th>
                    <th style={th}>Wins in a row</th><th style={th}>Losses in a row</th><th style={th}>Total R</th><th style={th}>Month</th>
                  </tr>
                </thead>
                <tbody>
                  {[...rows, first].map(r => {
                    const isFirst = r === first
                    return (
                      <tr key={r.label} style={{ borderTop: '1px solid var(--border)', textAlign: 'right', fontWeight: isFirst ? 800 : 500 }}>
                        <td style={{ textAlign: 'left', padding: '7px 8px', color: isFirst ? '#eab308' : 'var(--text-primary)' }}>{r.label}</td>
                        <td style={td}>{r.setups}</td><td style={td}>{r.takes}</td>
                        <td style={td}>{r.win} / {r.be} / {r.loss}</td>
                        <td style={{ ...td, color: r.bestW ? 'var(--bullish)' : td.color }}>{r.bestW}</td>
                        <td style={{ ...td, color: r.bestL ? 'var(--bearish)' : td.color }}>{r.bestL}</td>
                        <td style={{ ...td, color: rc(r.total) }}>{r.setups ? fmtR(r.total) : '—'}</td>
                        <td style={{ ...td, color: rc(r.total), fontWeight: 700 }}>{r.setups ? verdict(r.total) : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </details>
        ))}
      </div>
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ ...card, padding: '12px 14px' }}>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, marginTop: 3, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  )
}

const th: React.CSSProperties = { padding: '6px 8px', fontWeight: 700 }
const td: React.CSSProperties = { padding: '7px 8px', fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)' }
const stepBtn: React.CSSProperties = {
  width: 22, height: 22, display: 'grid', placeItems: 'center', borderRadius: 6, border: '1px solid var(--border)',
  background: 'var(--bg)', color: 'var(--text-secondary)', cursor: 'pointer',
}
const iconBtn: React.CSSProperties = {
  width: 26, height: 26, display: 'grid', placeItems: 'center', borderRadius: 6, border: '1px solid var(--border)',
  background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer',
}
