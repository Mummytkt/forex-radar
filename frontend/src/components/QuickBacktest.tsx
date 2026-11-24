'use client'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Zap, Star, Trash2, Pencil, Minus, Plus, Loader2, Trophy, CalendarDays, Wand2, Camera, Check, X, BookOpen } from 'lucide-react'
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
interface Res { outcome: Outcome | ''; takes: number; after_tp?: boolean }   // '' only in the form: ticked, result not picked yet
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
  const type = (raw: string) => {
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
  const bad = text.length === 10 && isoToDmy(value) !== text
  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <input value={text} onChange={e => type(e.target.value)} placeholder="DD/MM/YYYY" inputMode="numeric"
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
  poi_failed_at: string | null; watched_until: string; setup_end?: string; end_reason?: string; armed_at?: string | null; note: string }

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

function AutoCheck({ draft, onSaved }: { draft: Draft; onSaved: (r: AutoRes & { saved_id?: number; pictures?: number }) => void }) {
  const { timezone } = useTimezone()
  const [level, setLevel] = useState('')
  const [mode, setMode] = useState<'limit' | 'instant'>('limit')
  const [tol, setTol] = useState('1')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [res, setRes] = useState<AutoRes | null>(null)
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
    setBusy(true); setRes(null)
    const r = await api('/api/quick-bt/auto', { method: 'POST', body: JSON.stringify({ pair: draft.pair, side: draft.side,
      level: lv, mode, tol_pips: parseFloat(tol) || 0, start: zonedIso(draft.date, '00:00', timezone || 'UTC'),
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
        Put the breakout day in the date and type the level you watch (an OC: the first candle&apos;s close; a V: its level). Watching starts by itself once a whole H4 candle has moved away from your level. It finds every confirmation whose wick reaches the line and trades each one at TP 3R / BE 2R with your retakes. ★ first is the trade you&apos;d really take; the others keep being checked after its TP (marked &quot;after TP&quot;) until an H4 candle closes beyond the line, so each confirmation gets its own win rate.
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
                  <b style={{ color: col(t.outcome) }}>{t.outcome.toUpperCase()}</b>{t.exit ? ` (${when(t.exit)})` : ''}</span>
              ))}
            </div>
          ))}
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
  const [setups, setSetups] = useState<Setup[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<Draft>(() => blank())
  const [editId, setEditId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [rangeF, setRangeF] = useState<'all' | 'inside' | 'opposite'>('all')
  const [yearF, setYearF] = useState('all')
  const [showAll, setShowAll] = useState(false)
  const [reviewOnly, setReviewOnly] = useState(false)
  const [gallery, setGallery] = useState<Setup | null>(null)
  const [reading, setReading] = useState<Setup | null>(null)

  const load = useCallback(async () => {
    const r = await api('/api/quick-bt')
    if (r.ok) setSetups((await r.json()).setups)
    setLoading(false)
  }, [])
  useEffect(() => { load() }, [load])

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
  const edit = (s: Setup) => {
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
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Zap size={20} color="var(--accent)" /> Quick Backtest
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>
            Only you see this. One pass through the years: at each setup, tick every confirmation (H1, M15 OCTGD, M15 CISD, M5 CISD) that formed at the
            POI and star the first one. TP 3R, breakeven at 2R. Every trade you place counts: takes before the last are
            losses, and Win % is wins out of all trades.
          </p>
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
            try { localStorage.setItem(LAST_KEY, JSON.stringify({ pair: draft.pair, date: draft.date, range_type: draft.range_type })) } catch { /* private mode */ }
            setMsg(`Saved ✓ ${Object.keys(res.results).length} confirmation${Object.keys(res.results).length === 1 ? '' : 's'}, ${res.pictures ?? 0} picture${res.pictures === 1 ? '' : 's'} · marked to review. Next level.`)
            setDraft(d => ({ ...blank(), date: d.date, pair: d.pair, range_type: d.range_type, side: d.side }))
            load()
          }} />
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
          {msg && <div style={{ marginTop: 8, fontSize: 12.5, fontWeight: 600, color: msg.includes('✓') ? 'var(--bullish)' : msg.startsWith('Editing') ? 'var(--text-secondary)' : 'var(--bearish)' }}>{msg}</div>}
        </div>

        {/* ---------- results ---------- */}
        <div style={{ ...card, marginBottom: 18 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <h2 style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6, marginRight: 'auto' }}>
              <Trophy size={16} color="#eab308" /> Results ({shown.length} setup{shown.length === 1 ? '' : 's'})
            </h2>
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
        </div>

        {/* ---------- setups ---------- */}
        <div style={card}>
          <h2 style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 10 }}>Setups</h2>
          {loading ? <Loader2 size={18} className="spin" /> : setups.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No setups yet. Start at January 2020 and save your first one above.</p>
          ) : (
            <div style={{ display: 'grid', gap: 6 }}>
              {setups.some(s => s.auto && !s.reviewed) && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12.5 }}>
                  <button style={pill(reviewOnly, '#eab308')} onClick={() => setReviewOnly(v => !v)}>
                    To review ({setups.filter(s => s.auto && !s.reviewed).length})</button>
                  <span style={{ color: 'var(--text-muted)' }}>Auto-checked setups wait here until you look at their pictures and tick ✓.</span>
                </div>
              )}
              {reviewOnly && setups.filter(s => s.auto && !s.reviewed).map(s => (
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
              {!reviewOnly && (showAll ? setups : setups.slice(0, 40)).map(s => (
                <div key={s.id} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontSize: 12.5, padding: '7px 9px',
                  borderRadius: 8, border: '1px solid var(--border)', opacity: s.valid ? 1 : 0.55 }}>
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

// A setup read back as a page of the diary (user, 2026-11-24: "read the information like a book")
function SetupBook({ setup, onClose, onEdit, onReviewed }: { setup: Setup; onClose: () => void; onEdit: () => void; onReviewed: () => void }) {
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
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
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
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 400, background: 'rgba(0,0,0,0.85)', overflowY: 'auto', padding: 16 }}>
      <div onClick={e => e.stopPropagation()} className="fairy-diary dp-purple" style={{ maxWidth: 900, margin: '0 auto', background: 'var(--card)', borderRadius: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '10px 10px 0' }}>
          <button onClick={onClose} style={iconBtn} aria-label="Close"><X size={15} /></button>
        </div>
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
                <p className="dp-p">{r.text}</p>
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
              </span>
            </div>
          </div>
        </div>
      </div>
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
