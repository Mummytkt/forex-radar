'use client'
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import {
  Plus, Download, TrendingUp, TrendingDown, Target, Flame,
  Trophy, X, Edit2, Trash2, ChevronDown, Check, Minus,
  BookMarked, Zap, Star, Camera, Upload, ImageIcon, Eye, FileText,
  FlaskConical,
} from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import {
  TradeImage, getTradeImages, addTradeImage,
  deleteTradeImage, deleteAllTradeImages,
} from '@/lib/tradeImages'

// ── Config ────────────────────────────────────────────────────────────────────
export interface TradeLogConfig {
  tradeType: 'live' | 'backtest'
  pageTitle: string
  subtitle: string
  logButtonLabel: string
  emptyStateText: string
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface Entry {
  id: number
  trade_date: string
  instrument: string
  direction: string
  entry_price: number | null
  stop_loss: number | null
  take_profit: number | null
  exit_price: number | null
  pips: number | null
  rr_ratio: number | null
  amount_risked: number | null
  amount_aimed: number | null
  result: string
  setup_type: string
  setup_type_notes: string | null
  trade_type: string
  h4_break_type: string | null
  entry_date: string | null
  exit_date: string | null
  trigger_time: string | null
  entry_time: string | null
  exit_time: string | null
  session: string | null
  notes: string | null
  created_at: string
}

type Period = 'today' | 'week' | 'month' | 'year' | 'all'

// ── Constants ─────────────────────────────────────────────────────────────────
const RESULT_COLOR: Record<string, string> = {
  win: 'var(--bullish)',
  loss: 'var(--bearish)',
  breakeven: '#f59e0b',
  missed: '#8b5cf6',
  open: 'var(--accent)',
}
const RESULT_BG: Record<string, string> = {
  win: 'var(--bullish-bg)',
  loss: 'var(--bearish-bg)',
  breakeven: 'rgba(245,158,11,0.12)',
  missed: 'rgba(139,92,246,0.12)',
  open: 'var(--accent-bg)',
}
const RESULT_LABEL: Record<string, string> = {
  win: 'WIN', loss: 'LOSS', breakeven: 'BE', missed: 'MISSED', open: 'OPEN',
}
const SETUP_LABELS: Record<string, string> = {
  origin: 'Origin',
  continuation_ashape: 'Cont. A/V',
  continuation_h4oc: 'Cont. OC',
  continuation_h4breaker: 'Cont. Breaker',
  continuation_engulfing: 'Engulfing',
  other: 'Other',
}

function getSetupLabel(setupType: string, setupNotes: string | null): string {
  if (setupType === 'other' && setupNotes) return `Other: ${setupNotes}`
  return SETUP_LABELS[setupType] || setupType
}

const SESSION_LABELS: Record<string, string> = {
  london: 'London', new_york: 'New York', asian: 'Asian', other: 'Other',
}
const INSTRUMENTS = [
  'EUR/USD','GBP/USD','USD/JPY','USD/CHF','USD/CAD','AUD/USD','NZD/USD',
  'EUR/JPY','EUR/GBP','EUR/AUD','EUR/CAD','EUR/NZD','EUR/CHF',
  'GBP/JPY','GBP/AUD','GBP/CAD','GBP/NZD','GBP/CHF',
  'AUD/JPY','AUD/CAD','AUD/NZD','AUD/CHF','NZD/JPY','NZD/CAD','NZD/CHF',
  'CAD/JPY','CAD/CHF','CHF/JPY','XAU/USD',
  'WTI/USD','US30','NAS100','SPX500','UK100','GER40','JPN225',
  'BTC/USD','ETH/USD',
]
const PERIODS: { key: Period; label: string }[] = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This Week' },
  { key: 'month', label: 'This Month' },
  { key: 'year', label: 'This Year' },
  { key: 'all', label: 'All Time' },
]

// ── Auth helper ───────────────────────────────────────────────────────────────
function hdrs(): HeadersInit {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' }
           : { 'Content-Type': 'application/json' }
}

// ── Win-rate ring ─────────────────────────────────────────────────────────────
function WinRing({ rate }: { rate: number }) {
  const r = 26, cx = 32, cy = 32
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - rate / 100)
  const color = rate >= 65 ? 'var(--bullish)' : rate >= 45 ? 'var(--accent)' : 'var(--bearish)'
  return (
    <svg width={64} height={64} viewBox="0 0 64 64" style={{ flexShrink: 0 }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border)" strokeWidth={5} />
      <circle
        cx={cx} cy={cy} r={r} fill="none"
        stroke={color} strokeWidth={5}
        strokeDasharray={`${circ}`}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.5s ease' }}
      />
      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
        fill={color} fontSize="12" fontWeight="700" fontFamily="inherit">
        {Math.round(rate)}%
      </text>
    </svg>
  )
}

// ── Equity curve ──────────────────────────────────────────────────────────────
function EquityCurve({ entries }: { entries: Entry[] }) {
  const pts = useMemo(() => {
    return [...entries]
      .filter(e => e.result !== 'open' && e.pips !== null)
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
  }, [entries])

  if (pts.length < 2) {
    return (
      <div style={{
        height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--text-muted)', fontSize: 13, flexDirection: 'column', gap: 6,
      }}>
        <TrendingUp size={28} color="var(--text-muted)" />
        <span>Add at least 2 closed trades to see your equity curve</span>
      </div>
    )
  }

  const cumulative: number[] = []
  let sum = 0
  for (const p of pts) {
    // Honour the result field: if marked as a loss, negate the pips regardless
    // of how they were entered. Wins use absolute value to avoid double-negatives.
    const raw = p.pips!
    const contribution = p.result === 'loss' ? -Math.abs(raw) : p.result === 'win' ? Math.abs(raw) : raw
    sum += contribution
    cumulative.push(sum)
  }

  const W = 100, H = 35, PAD = 3
  const maxY = Math.max(0, ...cumulative)
  const minY = Math.min(0, ...cumulative)
  const range = maxY - minY || 1
  const toX = (i: number) => PAD + (i / (cumulative.length - 1)) * (W - 2 * PAD)
  const toY = (v: number) => PAD + (1 - (v - minY) / range) * (H - 2 * PAD)
  const zeroY = toY(Math.max(minY, Math.min(maxY, 0)))
  const linePoints = cumulative.map((v, i) => `${toX(i).toFixed(2)},${toY(v).toFixed(2)}`).join(' ')
  const areaPoints = [
    `${toX(0).toFixed(2)},${zeroY.toFixed(2)}`,
    ...cumulative.map((v, i) => `${toX(i).toFixed(2)},${toY(v).toFixed(2)}`),
    `${toX(cumulative.length - 1).toFixed(2)},${zeroY.toFixed(2)}`,
  ].join(' ')
  const final = cumulative[cumulative.length - 1]
  const positive = final >= 0
  const lineColor = positive ? 'var(--bullish)' : 'var(--bearish)'

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: lineColor }}>
          {final >= 0 ? '+' : ''}{final.toFixed(1)}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>pips cumulative · {pts.length} trades</span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ width: '100%', height: 120, display: 'block' }}
      >
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={positive ? '#22c55e' : '#ef4444'} stopOpacity="0.3" />
            <stop offset="100%" stopColor={positive ? '#22c55e' : '#ef4444'} stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1={PAD} y1={zeroY} x2={W - PAD} y2={zeroY}
          stroke="var(--border)" strokeWidth="0.5" strokeDasharray="1,1" />
        <polygon points={areaPoints} fill="url(#equityFill)" />
        <polyline points={linePoints} fill="none" stroke={lineColor} strokeWidth="1.2"
          strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={toX(cumulative.length - 1)} cy={toY(final)} r="1.5" fill={lineColor} />
      </svg>
    </div>
  )
}

// ── Default form ──────────────────────────────────────────────────────────────
function blank() {
  return {
    trade_date: '',
    instrument: '', direction: 'buy',
    entry_price: '', stop_loss: '', take_profit: '', exit_price: '',
    pips: '', rr_ratio: '',
    amount_risked: '', amount_aimed: '',
    result: 'open', setup_type: 'other',
    setup_type_notes: '',
    h4_break_type: '',
    entry_date: '', exit_date: '',
    trigger_time: '', entry_time: '', exit_time: '',
    session: '', notes: '',
  }
}

function fmtLongDate(iso: string): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })
}

// ── Lightbox ──────────────────────────────────────────────────────────────────
function Lightbox({ url, name, onClose }: { url: string; name: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 300,
        background: 'rgba(0,0,0,0.88)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: 20,
      }}
    >
      <button
        onClick={onClose}
        style={{
          position: 'absolute', top: 16, right: 16,
          width: 36, height: 36, borderRadius: '50%',
          background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.2)',
          color: 'white', cursor: 'pointer', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
        }}
      >
        <X size={16} />
      </button>
      <img
        src={url}
        alt={name}
        onClick={e => e.stopPropagation()}
        style={{
          maxWidth: '100%', maxHeight: 'calc(100vh - 80px)',
          borderRadius: 10, boxShadow: '0 8px 48px rgba(0,0,0,0.6)',
          objectFit: 'contain', display: 'block',
        }}
      />
      <div style={{
        marginTop: 12, fontSize: 12, color: 'rgba(255,255,255,0.6)',
        maxWidth: '80%', textAlign: 'center', wordBreak: 'break-all',
      }}>
        {name}
      </div>
    </div>
  )
}

// ── Image thumbnail strip ─────────────────────────────────────────────────────
function ImageStrip({
  label, existing, onDeleteExisting, pending, onAddPending, onRemovePending, onView,
}: {
  label: string
  existing: TradeImage[]
  onDeleteExisting: (id: number) => void
  pending: File[]
  onAddPending: (files: File[]) => void
  onRemovePending: (idx: number) => void
  onView: (url: string, name: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const pendingUrls = useMemo(() => pending.map(f => URL.createObjectURL(f)), [pending])

  useEffect(() => {
    return () => pendingUrls.forEach(u => URL.revokeObjectURL(u))
  }, [pendingUrls])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {label}
        </span>
        <button type="button" onClick={() => inputRef.current?.click()}
          style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0' }}>
          <Upload size={11} /> Add
        </button>
      </div>
      <input ref={inputRef} type="file" accept="image/*" multiple style={{ display: 'none' }}
        onChange={e => { if (e.target.files) onAddPending(Array.from(e.target.files)); e.target.value = '' }} />
      {existing.length === 0 && pending.length === 0 ? (
        <div onClick={() => inputRef.current?.click()}
          style={{ border: '1px dashed var(--border)', borderRadius: 8, padding: '14px', textAlign: 'center', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <ImageIcon size={14} /> Click to add screenshot
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {existing.map(img => (
            <ExistingThumb key={img.id} img={img} onDelete={() => onDeleteExisting(img.id)} onView={onView} />
          ))}
          {pendingUrls.map((url, i) => (
            <div key={i} style={{ position: 'relative' }}>
              <img src={url} alt={pending[i].name} onClick={() => onView(url, pending[i].name)}
                style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)', display: 'block', cursor: 'zoom-in' }} />
              <button type="button" onClick={e => { e.stopPropagation(); onRemovePending(i) }}
                style={{ position: 'absolute', top: -5, right: -5, width: 18, height: 18, borderRadius: '50%', background: 'var(--bearish)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <X size={9} />
              </button>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3, maxWidth: 72, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{pending[i].name}</div>
            </div>
          ))}
          <div onClick={() => inputRef.current?.click()}
            style={{ width: 72, height: 72, border: '1px dashed var(--border)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-muted)', flexShrink: 0 }}>
            <Plus size={18} />
          </div>
        </div>
      )}
    </div>
  )
}

function ExistingThumb({ img, onDelete, onView }: { img: TradeImage; onDelete: () => void; onView: (url: string, name: string) => void }) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    const u = URL.createObjectURL(img.blob)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [img.blob])
  if (!url) return null
  return (
    <div style={{ position: 'relative' }}>
      <img src={url} alt={img.name} onClick={() => onView(url, img.name)}
        style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)', display: 'block', cursor: 'zoom-in' }} />
      <button type="button" onClick={e => { e.stopPropagation(); onDelete() }}
        style={{ position: 'absolute', top: -5, right: -5, width: 18, height: 18, borderRadius: '50%', background: 'var(--bearish)', color: 'white', border: 'none', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <X size={9} />
      </button>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3, maxWidth: 72, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{img.name}</div>
    </div>
  )
}

// ── Inline result picker ──────────────────────────────────────────────────────
const RESULT_OPTIONS = [
  { v: 'win',       label: '✓ Win',   color: 'var(--bullish)', bg: 'var(--bullish-bg)' },
  { v: 'loss',      label: '✕ Loss',  color: 'var(--bearish)', bg: 'var(--bearish-bg)' },
  { v: 'missed',    label: 'Missed',  color: '#8b5cf6',        bg: 'rgba(139,92,246,0.12)' },
  { v: 'breakeven', label: 'B/E',     color: '#f59e0b',        bg: 'rgba(245,158,11,0.12)' },
  { v: 'open',      label: 'Open',    color: 'var(--accent)',  bg: 'var(--accent-bg)' },
] as const

function ResultPicker({ entry, onResultChange }: { entry: Entry; onResultChange: (id: number, result: string) => void }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, right: 0 })
  const btnRef = useRef<HTMLButtonElement>(null)
  const rc = RESULT_COLOR[entry.result] || 'var(--text-muted)'
  const rb = RESULT_BG[entry.result] || 'transparent'

  const handleOpen = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (btnRef.current) {
      const r = btnRef.current.getBoundingClientRect()
      setPos({ top: r.top, right: window.innerWidth - r.right })
    }
    setOpen(v => !v)
  }

  return (
    <div style={{ width: 58, flexShrink: 0, textAlign: 'center' }}>
      <button ref={btnRef} type="button" title="Tap to mark result" onClick={handleOpen}
        style={{ display: 'inline-block', fontSize: 10, fontWeight: 700, padding: '3px 6px', borderRadius: 5, background: rb, color: rc, border: `1px solid ${rc}`, cursor: 'pointer', minWidth: 44 }}>
        {RESULT_LABEL[entry.result] || entry.result.toUpperCase()}
      </button>
      {open && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 9998 }} onClick={e => { e.stopPropagation(); setOpen(false) }} />
          <div style={{ position: 'fixed', bottom: `${window.innerHeight - pos.top + 6}px`, right: `${pos.right}px`, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: '0 6px 24px rgba(0,0,0,0.5)', zIndex: 9999, overflow: 'hidden', minWidth: 120 }}>
            <p style={{ fontSize: 9, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '6px 10px 4px', margin: 0 }}>Mark as</p>
            {RESULT_OPTIONS.filter(o => o.v !== entry.result).map(o => (
              <button key={o.v} type="button"
                onClick={e => { e.stopPropagation(); onResultChange(entry.id, o.v); setOpen(false) }}
                style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 12px', border: 'none', background: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: o.color, textAlign: 'left' }}
                onMouseEnter={el => (el.currentTarget.style.background = o.bg)}
                onMouseLeave={el => (el.currentTarget.style.background = 'none')}
              >
                {o.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ── Trade row ─────────────────────────────────────────────────────────────────
function TradeRow({ entry, onView, onEdit, onDelete, onResultChange }: {
  entry: Entry
  onView: (e: Entry) => void
  onEdit: (e: Entry) => void
  onDelete: (id: number) => void
  onResultChange: (id: number, result: string) => void
}) {
  const rc = RESULT_COLOR[entry.result] || 'var(--text-muted)'
  const isBuy = entry.direction === 'buy'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', minWidth: 480, borderLeft: `3px solid ${rc}`, borderBottom: '1px solid var(--border)', background: 'var(--card)', transition: 'background 0.12s' }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--card-hover)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'var(--card)')}
    >
      <div style={{ width: 70, flexShrink: 0 }}>
        <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>{entry.trade_date.slice(5).replace('-', '/')}</p>
        <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{entry.trade_date.slice(0, 4)}</p>
      </div>
      <div style={{ width: 90, flexShrink: 0 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{entry.instrument}</p>
        <span style={{ display: 'inline-block', marginTop: 2, fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 4, background: isBuy ? 'var(--bullish-bg)' : 'var(--bearish-bg)', color: isBuy ? 'var(--bullish)' : 'var(--bearish)' }}>
          {isBuy ? '▲ BUY' : '▼ SELL'}
        </span>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {entry.entry_price != null || entry.exit_price != null ? (
          <p style={{ fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {entry.entry_price != null ? entry.entry_price : '—'}{' → '}{entry.exit_price != null ? entry.exit_price : '—'}
          </p>
        ) : null}
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
          {getSetupLabel(entry.setup_type, entry.setup_type_notes)}
          {entry.session ? ` · ${SESSION_LABELS[entry.session] || entry.session}` : ''}
        </p>
      </div>
      {(entry.amount_risked != null || entry.amount_aimed != null) && (
        <div style={{ width: 80, textAlign: 'right', flexShrink: 0 }}>
          {entry.amount_risked != null && <p style={{ fontSize: 10, color: 'var(--bearish)', fontWeight: 600 }}>−${entry.amount_risked.toFixed(0)}</p>}
          {entry.amount_aimed != null && <p style={{ fontSize: 10, color: 'var(--bullish)', fontWeight: 600, marginTop: 2 }}>+${entry.amount_aimed.toFixed(0)}</p>}
        </div>
      )}
      <div style={{ width: 60, textAlign: 'right', flexShrink: 0 }}>
        {entry.pips != null ? (
          <span style={{ fontSize: 13, fontWeight: 700, color: entry.pips >= 0 ? 'var(--bullish)' : 'var(--bearish)' }}>
            {entry.pips >= 0 ? '+' : ''}{entry.pips}
          </span>
        ) : <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>—</span>}
        {entry.rr_ratio != null && <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{entry.rr_ratio.toFixed(1)}R</p>}
      </div>
      <ResultPicker entry={entry} onResultChange={onResultChange} />
      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
        <button onClick={() => onView(entry)} title="View" style={{ width: 26, height: 26, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--accent-hover)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Eye size={11} /></button>
        <button onClick={() => onEdit(entry)} title="Edit" style={{ width: 26, height: 26, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Edit2 size={11} /></button>
        <button onClick={() => onDelete(entry.id)} title="Delete" style={{ width: 26, height: 26, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--bearish)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Trash2 size={11} /></button>
      </div>
    </div>
  )
}

// ── Trade detail view ─────────────────────────────────────────────────────────
function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value && value !== 0) return null
  return (
    <div style={{ display: 'flex', gap: 10, padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ width: 110, flexShrink: 0, fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', paddingTop: 1 }}>{label}</span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)', flex: 1 }}>{value}</span>
    </div>
  )
}

function TradeDetailModal({ entry, onClose, onEdit }: { entry: Entry; onClose: () => void; onEdit: () => void }) {
  const [existingBefore, setExistingBefore] = useState<TradeImage[]>([])
  const [existingAfter, setExistingAfter] = useState<TradeImage[]>([])
  const [lightbox, setLightbox] = useState<{ url: string; name: string } | null>(null)

  useEffect(() => {
    getTradeImages(entry.id, 'before').then(setExistingBefore)
    getTradeImages(entry.id, 'after').then(setExistingAfter)
  }, [entry.id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const rc = RESULT_COLOR[entry.result] || 'var(--text-muted)'
  const rb = RESULT_BG[entry.result] || 'transparent'
  const isBuy = entry.direction === 'buy'

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, width: '100%', maxWidth: 560, maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 24px 80px rgba(0,0,0,0.4)' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10, background: 'var(--surface)' }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            <span style={{ fontWeight: 800, fontSize: 17, color: 'var(--text-primary)' }}>{entry.instrument}</span>
            <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: isBuy ? 'var(--bullish-bg)' : 'var(--bearish-bg)', color: isBuy ? 'var(--bullish)' : 'var(--bearish)' }}>{isBuy ? '▲ BUY' : '▼ SELL'}</span>
            <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: rb, color: rc, border: `1px solid ${rc}` }}>{(RESULT_LABEL[entry.result] || entry.result).toUpperCase()}</span>
          </div>
          <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid var(--border)', background: 'var(--card-hover)', cursor: 'pointer', flexShrink: 0, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={14} /></button>
        </div>
        <div style={{ overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 0 }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Dates & Times</p>
          <DetailRow label="Log Date" value={entry.trade_date} />
          <DetailRow label="Entry Date" value={entry.entry_date ? fmtLongDate(entry.entry_date) : null} />
          <DetailRow label="Entry Time" value={entry.entry_time} />
          <DetailRow label="Exit Date" value={entry.exit_date ? fmtLongDate(entry.exit_date) : null} />
          <DetailRow label="Exit Time" value={entry.exit_time} />
          <DetailRow label="Trigger Time" value={entry.trigger_time} />
          <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 14, marginBottom: 4 }}>Price Levels</p>
          <DetailRow label="Entry Price" value={entry.entry_price} />
          <DetailRow label="Stop Loss" value={entry.stop_loss} />
          <DetailRow label="Take Profit" value={entry.take_profit} />
          <DetailRow label="Exit Price" value={entry.exit_price} />
          <DetailRow label="Pips" value={entry.pips != null ? `${entry.pips >= 0 ? '+' : ''}${entry.pips}` : null} />
          <DetailRow label="R:R Ratio" value={entry.rr_ratio != null ? `${entry.rr_ratio}R` : null} />
          {(entry.amount_risked != null || entry.amount_aimed != null) && <>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 14, marginBottom: 4 }}>Money</p>
            <DetailRow label="Amount Risked" value={entry.amount_risked != null ? `$${entry.amount_risked}` : null} />
            <DetailRow label="Amount Aimed" value={entry.amount_aimed != null ? `$${entry.amount_aimed}` : null} />
          </>}
          <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 14, marginBottom: 4 }}>Trade Info</p>
          <DetailRow label="Setup Type" value={getSetupLabel(entry.setup_type, entry.setup_type_notes)} />
          <DetailRow label="H4 Break Type" value={entry.h4_break_type ? entry.h4_break_type.charAt(0).toUpperCase() + entry.h4_break_type.slice(1) : null} />
          <DetailRow label="Session" value={entry.session ? (SESSION_LABELS[entry.session] || entry.session) : null} />
          {entry.notes && <>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 14, marginBottom: 4 }}>Notes</p>
            <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, whiteSpace: 'pre-wrap', padding: '8px 0' }}>{entry.notes}</p>
          </>}
          {(existingBefore.length > 0 || existingAfter.length > 0) && <>
            <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent-hover)', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 14, marginBottom: 8 }}>Chart Screenshots</p>
            {existingBefore.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Before (pre-trigger)</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {existingBefore.map(img => <ExistingThumb key={img.id} img={img} onDelete={() => {}} onView={(url, name) => setLightbox({ url, name })} />)}
                </div>
              </div>
            )}
            {existingAfter.length > 0 && (
              <div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>After (outcome)</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {existingAfter.map(img => <ExistingThumb key={img.id} img={img} onDelete={() => {}} onView={(url, name) => setLightbox({ url, name })} />)}
                </div>
              </div>
            )}
          </>}
        </div>
        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 10, background: 'var(--surface)' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '9px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--card-hover)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>Close</button>
          <button onClick={onEdit} style={{ flex: 1, padding: '9px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontWeight: 700, fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}><Edit2 size={13} /> Edit</button>
        </div>
      </div>
      {lightbox && <Lightbox url={lightbox.url} name={lightbox.name} onClose={() => setLightbox(null)} />}
    </div>
  )
}

// ── Trade modal ───────────────────────────────────────────────────────────────
type FormState = ReturnType<typeof blank>

function TradeModal({
  form, setForm, editing, saving, editEntryId, logButtonLabel, onSave, onClose,
}: {
  form: FormState
  setForm: (f: FormState) => void
  editing: boolean
  saving: boolean
  editEntryId?: number
  logButtonLabel: string
  onSave: (beforeFiles: File[], afterFiles: File[]) => void
  onClose: () => void
}) {
  const set = (k: keyof FormState, v: string) => setForm({ ...form, [k]: v })

  const [existingBefore, setExistingBefore] = useState<TradeImage[]>([])
  const [existingAfter, setExistingAfter] = useState<TradeImage[]>([])
  const [pendingBefore, setPendingBefore] = useState<File[]>([])
  const [pendingAfter, setPendingAfter] = useState<File[]>([])
  const [lightbox, setLightbox] = useState<{ url: string; name: string } | null>(null)

  useEffect(() => {
    if (editEntryId) {
      getTradeImages(editEntryId, 'before').then(setExistingBefore)
      getTradeImages(editEntryId, 'after').then(setExistingAfter)
    } else {
      setExistingBefore([]); setExistingAfter([])
    }
    setPendingBefore([]); setPendingAfter([])
  }, [editEntryId])

  const handleDeleteExisting = async (id: number, type: 'before' | 'after') => {
    await deleteTradeImage(id)
    if (type === 'before') setExistingBefore(p => p.filter(i => i.id !== id))
    else setExistingAfter(p => p.filter(i => i.id !== id))
  }

  const calcPips = (f: FormState) => {
    const entry = parseFloat(f.entry_price)
    const exit = parseFloat(f.exit_price)
    if (isNaN(entry) || isNaN(exit)) return f
    const instr = f.instrument.toUpperCase().replace('/', '')
    const pipSize = instr.endsWith('JPY') ? 0.01 : instr === 'XAUUSD' ? 0.1 : 0.0001
    const raw = f.direction === 'buy' ? (exit - entry) / pipSize : (entry - exit) / pipSize
    return { ...f, pips: raw.toFixed(1) }
  }

  const calcRR = (f: FormState) => {
    const entry = parseFloat(f.entry_price)
    const sl = parseFloat(f.stop_loss)
    const tp = parseFloat(f.take_profit)
    if (isNaN(entry) || isNaN(sl) || isNaN(tp)) return f
    const risk = Math.abs(entry - sl)
    const reward = Math.abs(tp - entry)
    if (risk === 0) return f
    return { ...f, rr_ratio: (reward / risk).toFixed(2) }
  }

  const handleChange = (k: keyof FormState, v: string) => {
    let f = { ...form, [k]: v }
    if (['entry_price', 'exit_price', 'instrument', 'direction'].includes(k)) f = calcPips(f)
    if (['entry_price', 'stop_loss', 'take_profit'].includes(k)) f = calcRR(f)
    if (['exit_price', 'direction', 'instrument'].includes(k)) {
      const p = parseFloat(f.pips)
      if (!isNaN(p) && f.result === 'open') {
        f = { ...f, result: p > 0 ? 'win' : p < 0 ? 'loss' : 'breakeven' }
      }
    }
    setForm(f)
  }

  const handleExitDateTimeChange = (k: 'exit_date' | 'exit_time', v: string) => {
    let f = { ...form, [k]: v }
    if (v && f.result === 'open') {
      const p = parseFloat(f.pips)
      f = { ...f, result: !isNaN(p) ? (p > 0 ? 'win' : p < 0 ? 'loss' : 'breakeven') : 'loss' }
    }
    setForm(f)
  }

  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
    textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, display: 'block',
  }
  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 10px', borderRadius: 8,
    border: '1px solid var(--border)', background: 'var(--surface)',
    color: 'var(--text-primary)', fontSize: 13, outline: 'none', boxSizing: 'border-box',
  }
  const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, width: '100%', maxWidth: 560, maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 24px 80px rgba(0,0,0,0.4)' }}>
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--surface)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <BookMarked size={14} color="var(--accent-hover)" />
            </div>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
              {editing ? 'Edit Entry' : logButtonLabel}
            </span>
          </div>
          <button onClick={onClose} style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid var(--border)', background: 'var(--card-hover)', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <X size={14} />
          </button>
        </div>

        {/* Form body */}
        <div style={{ overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Row 1: Date + Instrument */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Log Date</label>
              <input type="date" value={form.trade_date} onChange={e => set('trade_date', e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Instrument</label>
              <input list="instruments-list" value={form.instrument} onChange={e => handleChange('instrument', e.target.value)} placeholder="EUR/USD" style={inputStyle} />
              <datalist id="instruments-list">{INSTRUMENTS.map(i => <option key={i} value={i} />)}</datalist>
            </div>
          </div>

          {/* Row 2: Entry Date + Exit Date */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Entry Date</label>
              <input type="date" value={form.entry_date} onChange={e => set('entry_date', e.target.value)} style={inputStyle} />
              {form.entry_date && <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 5 }}>{fmtLongDate(form.entry_date)}</p>}
            </div>
            <div>
              <label style={labelStyle}>Exit Date</label>
              <input type="date" value={form.exit_date} onChange={e => handleExitDateTimeChange('exit_date', e.target.value)} style={inputStyle} />
              {form.exit_date && <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 5 }}>{fmtLongDate(form.exit_date)}</p>}
            </div>
          </div>

          {/* Trigger / Entry / Exit times */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div><label style={labelStyle}>Trigger Time</label><input type="time" value={form.trigger_time} onChange={e => set('trigger_time', e.target.value)} style={inputStyle} /></div>
            <div><label style={labelStyle}>Entry Time</label><input type="time" value={form.entry_time} onChange={e => set('entry_time', e.target.value)} style={inputStyle} /></div>
            <div><label style={labelStyle}>Exit Time</label><input type="time" value={form.exit_time} onChange={e => handleExitDateTimeChange('exit_time', e.target.value)} style={inputStyle} /></div>
          </div>

          {/* Direction toggle */}
          <div>
            <label style={labelStyle}>Direction</label>
            <div style={{ display: 'flex', gap: 0, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              {(['buy', 'sell'] as const).map(d => (
                <button key={d} onClick={() => handleChange('direction', d)} style={{ flex: 1, padding: '9px', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13, background: form.direction === d ? (d === 'buy' ? 'var(--bullish)' : 'var(--bearish)') : 'var(--surface)', color: form.direction === d ? 'white' : 'var(--text-primary)', transition: 'all 0.15s' }}>
                  {d === 'buy' ? '▲ Buy' : '▼ Sell'}
                </button>
              ))}
            </div>
          </div>

          {/* Result toggle */}
          <div>
            <label style={labelStyle}>Result</label>
            <div style={{ display: 'flex', gap: 0, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              {([
                { v: 'open',      label: 'Open',    activeColor: 'var(--accent)',   activeBg: 'var(--accent-bg)' },
                { v: 'win',       label: '✓ Win',   activeColor: 'var(--bullish)',  activeBg: 'var(--bullish-bg)' },
                { v: 'loss',      label: '✕ Loss',  activeColor: 'var(--bearish)',  activeBg: 'var(--bearish-bg)' },
                { v: 'missed',    label: 'Missed',  activeColor: '#8b5cf6',         activeBg: 'rgba(139,92,246,0.14)' },
                { v: 'breakeven', label: 'B/E',     activeColor: '#f59e0b',         activeBg: 'rgba(245,158,11,0.14)' },
              ] as const).map(({ v, label, activeColor, activeBg }) => (
                <button key={v} type="button" onClick={() => set('result', v)} style={{ flex: 1, padding: '10px 4px', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 12, background: form.result === v ? activeBg : 'var(--surface)', color: form.result === v ? activeColor : 'var(--text-secondary)', transition: 'all 0.15s', boxShadow: form.result === v ? `inset 0 -2px 0 ${activeColor}` : 'none' }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Entry / SL / TP / Exit */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {(['entry_price', 'stop_loss', 'take_profit', 'exit_price'] as const).map(k => (
              <div key={k}>
                <label style={labelStyle}>{k.replace(/_/g, ' ')}</label>
                <input type="number" step="any" value={form[k]} onChange={e => handleChange(k, e.target.value)} placeholder="0.00000" style={inputStyle} />
              </div>
            ))}
          </div>

          {/* Pips + R:R */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Pips (auto-calc)</label>
              <input type="number" step="any" value={form.pips} onChange={e => set('pips', e.target.value)} placeholder="+50" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>R:R ratio (auto-calc)</label>
              <input type="number" step="any" value={form.rr_ratio} onChange={e => set('rr_ratio', e.target.value)} placeholder="1.5" style={inputStyle} />
            </div>
          </div>

          {/* Amount Risked + Amount Aimed */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Amount Risked ($)</label>
              <input type="number" step="any" min="0" value={form.amount_risked} onChange={e => set('amount_risked', e.target.value)} placeholder="e.g. 50" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Amount Aimed ($)</label>
              <input type="number" step="any" min="0" value={form.amount_aimed} onChange={e => set('amount_aimed', e.target.value)} placeholder="e.g. 200" style={inputStyle} />
            </div>
          </div>

          {/* Setup type */}
          <div>
            <label style={labelStyle}>Setup type</label>
            <select value={form.setup_type} onChange={e => set('setup_type', e.target.value)} style={selectStyle}>
              <option value="origin">Origin</option>
              <option value="continuation_ashape">Continuation — A/V</option>
              <option value="continuation_h4oc">Continuation — OC</option>
              <option value="continuation_h4breaker">Continuation — Breaker</option>
              <option value="continuation_engulfing">Engulfing</option>
              <option value="other">Other</option>
            </select>
            {form.setup_type === 'other' && (
              <input
                type="text"
                value={form.setup_type_notes}
                onChange={e => set('setup_type_notes', e.target.value)}
                placeholder="Describe the setup (e.g. Break & Retest, Hammer)…"
                style={{ ...inputStyle, marginTop: 8 }}
              />
            )}
          </div>

          {/* H4 Break Type */}
          <div>
            <label style={labelStyle}>H4 Break Type</label>
            <div style={{ display: 'flex', gap: 0, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              {(['', 'internal', 'external'] as const).map(v => (
                <button key={v} type="button" onClick={() => set('h4_break_type', v)} style={{ flex: 1, padding: '9px', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12, background: form.h4_break_type === v ? 'var(--accent)' : 'var(--surface)', color: form.h4_break_type === v ? 'white' : 'var(--text-secondary)', transition: 'all 0.15s' }}>
                  {v === '' ? '— Not set' : v === 'internal' ? 'Internal' : 'External'}
                </button>
              ))}
            </div>
          </div>

          {/* Session */}
          <div>
            <label style={labelStyle}>Session (optional)</label>
            <select value={form.session} onChange={e => set('session', e.target.value)} style={selectStyle}>
              <option value="">— Select —</option>
              <option value="asian">Asian</option>
              <option value="london">London</option>
              <option value="new_york">New York</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Notes */}
          <div>
            <label style={labelStyle}>Notes</label>
            <textarea value={form.notes} onChange={e => set('notes', e.target.value)}
              placeholder="What went well? What would you do differently?"
              rows={3} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5, fontFamily: 'inherit' }} />
          </div>

          {/* Charts section */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 }}>
              <Camera size={13} color="var(--accent-hover)" />
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>Chart Screenshots</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 2 }}>saved in browser only — no server upload</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <ImageStrip label="Before (pre-trigger analysis)" existing={existingBefore} onDeleteExisting={id => handleDeleteExisting(id, 'before')} pending={pendingBefore} onAddPending={files => setPendingBefore(p => [...p, ...files])} onRemovePending={idx => setPendingBefore(p => p.filter((_, i) => i !== idx))} onView={(url, name) => setLightbox({ url, name })} />
              <ImageStrip label="After (outcome / review)" existing={existingAfter} onDeleteExisting={id => handleDeleteExisting(id, 'after')} pending={pendingAfter} onAddPending={files => setPendingAfter(p => [...p, ...files])} onRemovePending={idx => setPendingAfter(p => p.filter((_, i) => i !== idx))} onView={(url, name) => setLightbox({ url, name })} />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 10, background: 'var(--surface)' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '10px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--card-hover)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>Cancel</button>
          <button onClick={() => onSave(pendingBefore, pendingAfter)} disabled={saving || !form.instrument || !form.trade_date}
            style={{ flex: 2, padding: '10px', borderRadius: 8, border: 'none', background: saving ? 'var(--accent-bg)' : 'var(--accent)', color: 'white', cursor: saving ? 'default' : 'pointer', fontWeight: 700, fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            {saving ? 'Saving…' : (<><Check size={14} /> {editing ? 'Save Changes' : logButtonLabel}</>)}
          </button>
        </div>
      </div>
      {lightbox && <Lightbox url={lightbox.url} name={lightbox.name} onClose={() => setLightbox(null)} />}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function TradeLogPage({ config }: { config: TradeLogConfig }) {
  const [entries, setEntries] = useState<Entry[]>([])
  const [period, setPeriod] = useState<Period>('month')
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editEntry, setEditEntry] = useState<Entry | null>(null)
  const [viewEntry, setViewEntry] = useState<Entry | null>(null)
  const [form, setForm] = useState(blank())
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/api/journal?period=${period}&trade_type=${config.tradeType}`, { headers: hdrs() })
      const data = await r.json()
      setEntries(Array.isArray(data) ? data : [])
    } catch { setEntries([]) }
    finally { setLoading(false) }
  }, [period, config.tradeType])

  useEffect(() => { load() }, [load])

  // ── Stats ──────────────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    const closed = entries.filter(e => e.result !== 'open')
    const wins = closed.filter(e => e.result === 'win').length
    const losses = closed.filter(e => e.result === 'loss').length
    const breakeven = closed.filter(e => e.result === 'breakeven').length
    const missed = closed.filter(e => e.result === 'missed').length
    const open = entries.filter(e => e.result === 'open').length
    const decided = closed.filter(e => e.result === 'win' || e.result === 'loss')
    const totalPips = closed.reduce((s, e) => s + (e.pips ?? 0), 0)
    const avgPips = closed.length ? totalPips / closed.length : 0
    const winRate = decided.length ? (wins / decided.length) * 100 : 0
    const bestPips = closed.filter(e => e.pips != null).reduce((m, e) => Math.max(m, e.pips!), -Infinity)
    const rrArr = closed.filter(e => e.rr_ratio != null).map(e => e.rr_ratio!)
    const avgRR = rrArr.length ? rrArr.reduce((s, v) => s + v, 0) / rrArr.length : null
    const riskedEntries = closed.filter(e => e.amount_risked != null && e.amount_aimed != null)
    const netPnl = riskedEntries.reduce((s, e) => {
      if (e.result === 'win') return s + (e.amount_aimed ?? 0)
      if (e.result === 'loss') return s - (e.amount_risked ?? 0)
      return s
    }, 0)
    let streak = 0, streakType = 'none'
    const sorted = [...closed].sort((a, b) => b.trade_date.localeCompare(a.trade_date))
    if (sorted.length) {
      const first = sorted[0].result
      if (first === 'win' || first === 'loss') {
        streakType = first
        for (const e of sorted) { if (e.result === first) streak++; else break }
      }
    }
    return { total: entries.length, wins, losses, breakeven, missed, open, totalPips, avgPips, winRate, bestPips: isFinite(bestPips) ? bestPips : null, avgRR, streak, streakType, netPnl, hasPnl: riskedEntries.length > 0 }
  }, [entries])

  // ── Modal helpers ──────────────────────────────────────────────────────────
  const openAdd = () => {
    setEditEntry(null)
    setForm({ ...blank(), trade_date: new Date().toISOString().split('T')[0] })
    setModalOpen(true)
  }
  const openEdit = (e: Entry) => {
    setEditEntry(e)
    setForm({
      trade_date: e.trade_date, instrument: e.instrument, direction: e.direction,
      entry_price: e.entry_price?.toString() ?? '',
      stop_loss: e.stop_loss?.toString() ?? '',
      take_profit: e.take_profit?.toString() ?? '',
      exit_price: e.exit_price?.toString() ?? '',
      pips: e.pips?.toString() ?? '',
      rr_ratio: e.rr_ratio?.toString() ?? '',
      amount_risked: e.amount_risked?.toString() ?? '',
      amount_aimed: e.amount_aimed?.toString() ?? '',
      result: e.result, setup_type: e.setup_type,
      setup_type_notes: e.setup_type_notes ?? '',
      h4_break_type: e.h4_break_type ?? '',
      entry_date: e.entry_date ?? '', exit_date: e.exit_date ?? '',
      trigger_time: e.trigger_time ?? '', entry_time: e.entry_time ?? '', exit_time: e.exit_time ?? '',
      session: e.session ?? '', notes: e.notes ?? '',
    })
    setModalOpen(true)
  }

  const save = async (beforeFiles: File[], afterFiles: File[]) => {
    if (!form.instrument || !form.trade_date) return
    setSaving(true)
    const body = {
      trade_date: form.trade_date, instrument: form.instrument, direction: form.direction,
      entry_price: form.entry_price ? parseFloat(form.entry_price) : null,
      stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
      take_profit: form.take_profit ? parseFloat(form.take_profit) : null,
      exit_price: form.exit_price ? parseFloat(form.exit_price) : null,
      pips: form.pips ? parseFloat(form.pips) : null,
      rr_ratio: form.rr_ratio ? parseFloat(form.rr_ratio) : null,
      amount_risked: form.amount_risked ? parseFloat(form.amount_risked) : null,
      amount_aimed: form.amount_aimed ? parseFloat(form.amount_aimed) : null,
      result: form.result, setup_type: form.setup_type,
      setup_type_notes: form.setup_type_notes || null,
      trade_type: config.tradeType,
      h4_break_type: form.h4_break_type || null,
      entry_date: form.entry_date || null,
      exit_date: form.exit_date || null,
      trigger_time: form.trigger_time || null,
      entry_time: form.entry_time || null,
      exit_time: form.exit_time || null,
      session: form.session || null, notes: form.notes || null,
    }
    try {
      const url = editEntry ? `${API_BASE}/api/journal/${editEntry.id}` : `${API_BASE}/api/journal`
      const resp = await fetch(url, { method: editEntry ? 'PUT' : 'POST', headers: hdrs(), body: JSON.stringify(body) })
      const saved = await resp.json()
      const tradeId: number = saved.id
      for (const f of beforeFiles) await addTradeImage(tradeId, 'before', f)
      for (const f of afterFiles) await addTradeImage(tradeId, 'after', f)
      setModalOpen(false); load()
    } catch { /* TODO: toast error */ }
    finally { setSaving(false) }
  }

  const deleteEntry = async (id: number) => {
    await fetch(`${API_BASE}/api/journal/${id}`, { method: 'DELETE', headers: hdrs() })
    await deleteAllTradeImages(id)
    setConfirmDelete(null); load()
  }

  const handleResultChange = async (id: number, result: string) => {
    setEntries(es => es.map(e => e.id === id ? { ...e, result } : e))
    await fetch(`${API_BASE}/api/journal/${id}`, { method: 'PUT', headers: hdrs(), body: JSON.stringify({ result }) })
  }

  const [showExportMenu, setShowExportMenu] = useState(false)
  useEffect(() => {
    if (!showExportMenu) return
    const close = () => setShowExportMenu(false)
    window.addEventListener('click', close, { capture: true, once: true })
    return () => window.removeEventListener('click', close, { capture: true })
  }, [showExportMenu])

  const exportCsv = () => {
    const headers = ['Date','Instrument','Direction','Result','Entry','SL','TP','Exit','Pips','R:R','Amount Risked','Amount Aimed','Setup','Setup Notes','H4 Break Type','Entry Date','Entry Time','Exit Date','Exit Time','Trigger Time','Session','Notes']
    const rows = entries.map(e => [
      e.trade_date, e.instrument, e.direction.toUpperCase(), e.result.toUpperCase(),
      e.entry_price ?? '', e.stop_loss ?? '', e.take_profit ?? '', e.exit_price ?? '',
      e.pips ?? '', e.rr_ratio ?? '',
      e.amount_risked ?? '', e.amount_aimed ?? '',
      SETUP_LABELS[e.setup_type] || e.setup_type,
      e.setup_type_notes ?? '',
      e.h4_break_type ?? '',
      e.entry_date ? fmtLongDate(e.entry_date) : '', e.entry_time ?? '',
      e.exit_date ? fmtLongDate(e.exit_date) : '', e.exit_time ?? '',
      e.trigger_time ?? '',
      e.session ?? '', (e.notes ?? '').replace(/,/g, ';'),
    ])
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    a.download = `${config.tradeType}-${period}-${new Date().toISOString().slice(0,10)}.csv`
    a.click()
    setShowExportMenu(false)
  }

  const exportPdf = () => {
    setShowExportMenu(false)
    const periodLabel = PERIODS.find(p => p.key === period)?.label ?? 'All Time'
    const now = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
    const rows = entries.map(e => `
      <tr>
        <td>${e.trade_date}</td>
        <td><strong>${e.instrument}</strong></td>
        <td class="${e.direction}">${e.direction.toUpperCase()}</td>
        <td>${e.entry_price ?? '—'}</td>
        <td>${e.exit_price ?? '—'}</td>
        <td class="${e.pips != null ? (e.pips >= 0 ? 'win' : 'loss') : ''}">${e.pips != null ? (e.pips >= 0 ? '+' : '') + e.pips : '—'}</td>
        <td>${e.rr_ratio != null ? e.rr_ratio + 'R' : '—'}</td>
        <td>${e.h4_break_type ?? '—'}</td>
        <td class="${e.result}">${(RESULT_LABEL[e.result] || e.result).toUpperCase()}</td>
        <td>${(e.notes ?? '').replace(/</g, '&lt;').replace(/\n/g, '<br/>')}</td>
      </tr>`).join('')
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>${config.pageTitle} — ${periodLabel}</title>
<style>
  body{font-family:Arial,sans-serif;font-size:11px;color:#111;margin:24px;}
  h1{font-size:20px;margin:0 0 4px;}
  .meta{color:#666;font-size:10px;margin-bottom:18px;}
  table{width:100%;border-collapse:collapse;}
  th{background:#e8eaf0;border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.05em;}
  td{border:1px solid #ddd;padding:6px 8px;vertical-align:top;}
  tr:nth-child(even) td{background:#fafafa;}
  .win{color:#16a34a;font-weight:700;} .loss{color:#dc2626;font-weight:700;}
  .buy{color:#16a34a;} .sell{color:#dc2626;}
  .open{color:#4f46e5;} .breakeven{color:#d97706;font-weight:700;} .missed{color:#8b5cf6;font-weight:700;}
  @media print{body{margin:10px;}}
</style></head><body>
<h1>MummyTKT's Bias Pointer — ${config.pageTitle}</h1>
<p class="meta">Period: ${periodLabel} &nbsp;·&nbsp; Generated: ${now} &nbsp;·&nbsp; ${entries.length} trade${entries.length !== 1 ? 's' : ''}</p>
<table><thead><tr>
  <th>Date</th><th>Instrument</th><th>Direction</th>
  <th>Entry</th><th>Exit</th><th>Pips</th><th>R:R</th>
  <th>H4 Type</th><th>Result</th><th>Notes</th>
</tr></thead><tbody>${rows}</tbody></table>
</body></html>`
    const w = window.open('', '_blank')
    if (w) { w.document.write(html); w.document.close(); setTimeout(() => w.print(), 400) }
  }

  const pipsColor = stats.totalPips >= 0 ? 'var(--bullish)' : 'var(--bearish)'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <TopBar title={config.pageTitle} />

      <main style={{ flex: 1, padding: '20px 24px', maxWidth: 900, margin: '0 auto', width: '100%' }}>

        {/* ── Page header ── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              {config.tradeType === 'backtest'
                ? <FlaskConical size={20} color="var(--accent)" />
                : <BookMarked size={20} color="var(--accent)" />}
              {config.pageTitle}
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>{config.subtitle}</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ position: 'relative' }}>
              <button onClick={() => setShowExportMenu(v => !v)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                <Download size={14} /> Export <ChevronDown size={12} />
              </button>
              {showExportMenu && (
                <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 4px)', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.3)', zIndex: 50, overflow: 'hidden', minWidth: 160 }}>
                  <button onClick={exportCsv} style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '10px 14px', border: 'none', background: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13, textAlign: 'left' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--card-hover)')} onMouseLeave={e => (e.currentTarget.style.background = 'none')}>
                    <Download size={13} /> Download CSV
                  </button>
                  <button onClick={exportPdf} style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '10px 14px', border: 'none', background: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: 13, textAlign: 'left' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--card-hover)')} onMouseLeave={e => (e.currentTarget.style.background = 'none')}>
                    <FileText size={13} /> Download PDF
                  </button>
                </div>
              )}
            </div>
            <button onClick={openAdd} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontSize: 13, fontWeight: 700, boxShadow: '0 2px 8px rgba(99,102,241,0.35)' }}>
              <Plus size={14} /> {config.logButtonLabel}
            </button>
          </div>
        </div>

        {/* ── Period tabs ── */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, width: 'fit-content' }}>
          {PERIODS.map(p => (
            <button key={p.key} onClick={() => setPeriod(p.key)} style={{ padding: '6px 14px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, background: period === p.key ? 'var(--accent)' : 'transparent', color: period === p.key ? 'white' : 'var(--text-secondary)', transition: 'all 0.15s', boxShadow: period === p.key ? '0 1px 6px rgba(99,102,241,0.3)' : 'none' }}>
              {p.label}
            </button>
          ))}
        </div>

        {/* ── Stats grid ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Trades</span>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Target size={14} color="var(--accent-hover)" /></div>
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1 }}>{stats.total}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <span style={{ fontSize: 11, color: 'var(--bullish)', fontWeight: 600 }}>{stats.wins}W</span>
              <span style={{ fontSize: 11, color: 'var(--bearish)', fontWeight: 600 }}>{stats.losses}L</span>
              {stats.breakeven > 0 && <span style={{ fontSize: 11, color: '#f59e0b', fontWeight: 600 }}>{stats.breakeven}BE</span>}
              {stats.missed > 0 && <span style={{ fontSize: 11, color: '#8b5cf6', fontWeight: 600 }}>{stats.missed}M</span>}
              {stats.open > 0 && <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>{stats.open} open</span>}
            </div>
            {stats.total > 0 && (
              <div style={{ height: 4, borderRadius: 4, background: 'var(--border)', marginTop: 10, overflow: 'hidden' }}>
                <div style={{ height: '100%', borderRadius: 4, background: 'var(--bullish)', width: `${(stats.wins / stats.total) * 100}%`, transition: 'width 0.8s ease' }} />
              </div>
            )}
          </div>

          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Win Rate</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <WinRing rate={stats.winRate} />
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{stats.wins} wins</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>of {stats.wins + stats.losses} decided</div>
                {stats.avgRR != null && <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 4, fontWeight: 600 }}>avg {stats.avgRR.toFixed(1)}R</div>}
              </div>
            </div>
          </div>

          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stats.hasPnl ? 'Net P&L' : 'Net Pips'}</span>
              <div style={{ width: 30, height: 30, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: stats.totalPips >= 0 ? 'var(--bullish-bg)' : 'var(--bearish-bg)' }}>
                {stats.totalPips >= 0 ? <TrendingUp size={14} color="var(--bullish)" /> : <TrendingDown size={14} color="var(--bearish)" />}
              </div>
            </div>
            {stats.hasPnl ? (
              <>
                <div style={{ fontSize: 30, fontWeight: 800, color: stats.netPnl >= 0 ? 'var(--bullish)' : 'var(--bearish)', lineHeight: 1 }}>{stats.netPnl >= 0 ? '+' : ''}${Math.abs(stats.netPnl).toFixed(0)}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{stats.totalPips >= 0 ? '+' : ''}{stats.totalPips.toFixed(1)} pips</div>
              </>
            ) : (
              <>
                <div style={{ fontSize: 30, fontWeight: 800, color: pipsColor, lineHeight: 1 }}>{stats.totalPips >= 0 ? '+' : ''}{stats.totalPips.toFixed(1)}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>avg {stats.avgPips >= 0 ? '+' : ''}{stats.avgPips.toFixed(1)} per trade</div>
              </>
            )}
          </div>

          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Streak</span>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: 'rgba(251,191,36,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {stats.streak >= 3 && stats.streakType === 'win' ? <Flame size={14} color="#f59e0b" /> : <Zap size={14} color="var(--accent-hover)" />}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ fontSize: 30, fontWeight: 800, lineHeight: 1, color: stats.streakType === 'win' ? 'var(--bullish)' : stats.streakType === 'loss' ? 'var(--bearish)' : 'var(--text-muted)' }}>
                {stats.streak || '—'}
              </span>
              {stats.streak > 0 && <span style={{ fontSize: 14, fontWeight: 700, color: stats.streakType === 'win' ? 'var(--bullish)' : 'var(--bearish)' }}>{stats.streakType === 'win' ? 'W' : 'L'}</span>}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              {stats.streak === 0 ? 'No streak' : stats.streakType === 'win' ? `${stats.streak >= 5 ? '🔥 ' : ''}Winning run` : 'Losing run'}
            </div>
          </div>
        </div>

        {/* ── Equity curve ── */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '18px 20px', marginBottom: 16 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 14 }}>Equity Curve</h2>
          <EquityCurve entries={entries} />
        </div>

        {/* ── Trades list ── */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--surface)' }}>
            <h2 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              {config.tradeType === 'backtest' ? 'Backtest Log' : 'Trade Log'}
            </h2>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{entries.length} {entries.length === 1 ? 'entry' : 'entries'}</span>
          </div>

          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
          ) : entries.length === 0 ? (
            <div style={{ padding: '48px 20px', textAlign: 'center' }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
                {config.tradeType === 'backtest' ? <FlaskConical size={24} color="var(--accent-hover)" /> : <BookMarked size={24} color="var(--accent-hover)" />}
              </div>
              <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', marginBottom: 6 }}>
                {config.tradeType === 'backtest' ? 'No backtests yet' : 'No trades yet'}
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 18 }}>{config.emptyStateText}</p>
              <button onClick={openAdd} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>
                <Plus size={14} /> {config.logButtonLabel}
              </button>
            </div>
          ) : (
            <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' as 'auto' }}>
              {entries.map(e => (
                <TradeRow key={e.id} entry={e} onView={setViewEntry} onEdit={openEdit} onDelete={id => setConfirmDelete(id)} onResultChange={handleResultChange} />
              ))}
            </div>
          )}
        </div>
      </main>

      {viewEntry && <TradeDetailModal entry={viewEntry} onClose={() => setViewEntry(null)} onEdit={() => { openEdit(viewEntry); setViewEntry(null) }} />}

      {modalOpen && (
        <TradeModal
          form={form} setForm={setForm}
          editing={!!editEntry} saving={saving}
          editEntryId={editEntry?.id}
          logButtonLabel={config.logButtonLabel}
          onSave={save}
          onClose={() => setModalOpen(false)}
        />
      )}

      {confirmDelete !== null && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
          onClick={e => { if (e.target === e.currentTarget) setConfirmDelete(null) }}>
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px 28px', maxWidth: 340, textAlign: 'center' }}>
            <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'var(--bearish-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
              <Trash2 size={18} color="var(--bearish)" />
            </div>
            <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', marginBottom: 6 }}>Delete this entry?</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>This cannot be undone. Chart screenshots stored in your browser will also be removed.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setConfirmDelete(null)} style={{ flex: 1, padding: '9px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-secondary)', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>Cancel</button>
              <button onClick={() => deleteEntry(confirmDelete)} style={{ flex: 1, padding: '9px', borderRadius: 8, border: 'none', background: 'var(--bearish)', color: 'white', cursor: 'pointer', fontWeight: 700, fontSize: 13 }}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
