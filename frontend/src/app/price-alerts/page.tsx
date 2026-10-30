'use client'
import { useState, useEffect } from 'react'
import useSWR, { mutate } from 'swr'
import { Target, Trash2, Clock, CheckCircle2, Bell, Pencil, Zap } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher, API_BASE } from '@/lib/api'
import type { InstrumentOverview, PriceAlertsList, PriceAlertItem, EntryAlertsList, EntryAlertItem } from '@/lib/types'

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeaders(): HeadersInit {
  if (typeof window === 'undefined') return {}
  const t = localStorage.getItem('mbp_token')
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

function formatPrice(instrument: string, price: number): string {
  if (instrument.endsWith('JPY')) return price.toFixed(3)
  if (instrument === 'XAGUSD') return price.toFixed(3)
  if (['XAUUSD', 'USOIL', 'WTIUSD'].includes(instrument)) return price.toFixed(2)
  if (['US30', 'NAS100', 'SPX500', 'UK100', 'GER40', 'JPN225'].includes(instrument)) return price.toFixed(0)
  return price.toFixed(5)
}

function expiryFromPreset(preset: string): string | null {
  const now = new Date()
  if (preset === 'eod') {
    const eod = new Date(now)
    eod.setUTCHours(23, 59, 59, 0)
    return eod.toISOString()
  }
  if (preset === '1week') {
    const d = new Date(now.getTime() + 7 * 86400000)
    return d.toISOString()
  }
  if (preset === '1month') {
    const d = new Date(now.getTime() + 30 * 86400000)
    return d.toISOString()
  }
  return null
}

function conditionLabel(c: string): string {
  if (c === 'crossing_up') return 'Closes above'
  if (c === 'crossing_down') return 'Closes below'
  if (c === 'rejects') return 'Rejects level'
  return 'Crosses (either)'
}

function alertPreview(
  instrument: string,
  triggerType: string,
  timeframe: string,
  condition: string,
  priceStr: string,
  currentPrice: number | undefined,
): string {
  const priceVal = parseFloat(priceStr)
  if (!instrument || isNaN(priceVal) || priceVal <= 0) return ''
  const fmt = formatPrice(instrument, priceVal)
  const candle = triggerType === 'on_candle_close' ? `${timeframe === '1D' ? 'Daily' : timeframe === '1W' ? 'Weekly' : timeframe} candle` : null

  if (condition === 'crossing_up') {
    const base = candle
      ? `One Telegram message when a ${candle} closes above ${fmt}.`
      : `One Telegram message when price touches ${fmt} from below.`
    if (currentPrice !== undefined && currentPrice > priceVal)
      return base + ` Price is currently above it — a candle has to close below ${fmt} first.`
    return base
  }
  if (condition === 'crossing_down') {
    const base = candle
      ? `One Telegram message when a ${candle} closes below ${fmt}.`
      : `One Telegram message when price touches ${fmt} from above.`
    if (currentPrice !== undefined && currentPrice < priceVal)
      return base + ` Price is currently below it — a candle has to close above ${fmt} first.`
    return base
  }
  if (condition === 'rejects') {
    return candle
      ? `One Telegram message when a ${candle} wicks to ${fmt} and closes back on the same side.`
      : `One Telegram message when price wicks to ${fmt} and closes back on the side it came from.`
  }
  return candle
    ? `One Telegram message when a ${candle} closes on either side of ${fmt}.`
    : `One Telegram message when price crosses through ${fmt} in either direction.`
}

function triggerLabel(t: string, tf?: string): string {
  if (t === 'on_candle_close') return tf ? `Candle close · ${tf}` : 'On candle close'
  return 'On touch'
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

// ── Alert row component ───────────────────────────────────────────────────────

function AlertRow({ item, onDelete, onEdit }: { item: PriceAlertItem; onDelete: (id: number) => void; onEdit: (item: PriceAlertItem) => void }) {
  const triggered = !!item.triggered_at
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 8, flexShrink: 0,
        background: triggered ? 'var(--bullish-bg)' : 'var(--accent-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {triggered
          ? <CheckCircle2 size={14} color="var(--bullish)" />
          : <Target size={14} color="var(--accent-hover)" />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>{item.instrument}</span>
          <span style={{
            fontSize: 11, padding: '2px 7px', borderRadius: 5,
            background: 'var(--border)', color: 'var(--text-secondary)',
          }}>
            {conditionLabel(item.condition)}
          </span>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-hover)' }}>
            {formatPrice(item.instrument, item.price)}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 3, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {triggerLabel(item.trigger_type, item.timeframe)}
          </span>
          {item.message && (
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>· {item.message}</span>
          )}
          {triggered && item.triggered_at && (
            <span style={{ fontSize: 11, color: 'var(--bullish)' }}>· Triggered {timeAgo(item.triggered_at)}</span>
          )}
          {!triggered && item.expires_at && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · Expires {timeAgo(item.expires_at).replace('ago', 'left')}
            </span>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 5, flexShrink: 0 }}>
        {!triggered && (
          <button
            onClick={() => onEdit(item)}
            style={{
              width: 28, height: 28, borderRadius: 7, border: 'none', cursor: 'pointer',
              background: 'var(--border)', color: 'var(--text-muted)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.1s',
            }}
            title="Edit"
          >
            <Pencil size={11} />
          </button>
        )}
        <button
          onClick={() => onDelete(item.id)}
          style={{
            width: 28, height: 28, borderRadius: 7, border: 'none', cursor: 'pointer',
            background: 'var(--border)', color: 'var(--text-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.1s',
          }}
          title="Delete"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

// ── Entry Pattern Alert row ───────────────────────────────────────────────────

// The formations a level can watch: "<timeframe>:<pattern>"
const ENTRY_WATCHES: { key: string; label: string; hint: string }[] = [
  { key: 'H1:sweep',        label: 'H1 Sweep',            hint: "a bullish candle wicks below the bearish candle before it and closes back above that low (sell: mirror)" },
  { key: 'H2:sweep',        label: 'H2 Sweep',            hint: 'the same on 2-hour candles' },
  { key: 'M15:sweep_break', label: 'M15 Sweep and Break', hint: 'a low at the level, its sweep, then a close above the last lower high' },
  { key: 'M5:sweep_break',  label: 'M5 Sweep and Break',  hint: 'the same on 5-minute candles' },
  { key: 'H1:pcl',          label: 'H1 PCL',              hint: "MummyTKT's PCL on H1" },
  { key: 'H2:pcl',          label: 'H2 PCL',              hint: "MummyTKT's PCL on H2" },
]
const ENTRY_DEFAULT_WATCHES = ['H1:sweep', 'H2:sweep', 'M15:sweep_break', 'M5:sweep_break']
const watchLabel = (k: string) => ENTRY_WATCHES.find(w => w.key === k)?.label ?? k
const patternLabel = (p: string) => p === 'pcl' ? 'PCL' : p === 'sweep_break' ? 'Sweep and Break' : 'Sweep'

function EntryAlertRow({ item, onDelete }: { item: EntryAlertItem; onDelete: (id: number) => void }) {
  const triggered = !!item.triggered_at
  const dirLabel = item.direction === 'bullish' ? 'Buy' : 'Sell'
  const dirColor = item.direction === 'bullish' ? 'var(--bullish)' : 'var(--bearish)'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 8, flexShrink: 0,
        background: triggered ? 'var(--bullish-bg)' : 'var(--accent-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {triggered
          ? <CheckCircle2 size={14} color="var(--bullish)" />
          : <Zap size={14} color="var(--accent-hover)" />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>{item.instrument}</span>
          <span style={{
            fontSize: 11, padding: '2px 7px', borderRadius: 5,
            background: 'var(--border)', color: dirColor, fontWeight: 600,
          }}>
            {dirLabel}
          </span>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-hover)' }}>
            {formatPrice(item.instrument, item.price)}
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            ± {item.tolerance_pips}p
          </span>
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 3, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {item.watches ? item.watches.map(watchLabel).join(' · ') : 'PCL or Engulfing Sweep · H1/H2'}
            {item.keep_open ? ' · keeps watching' : ''}
          </span>
          {item.note && (
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>· {item.note}</span>
          )}
          {triggered && item.triggered_pattern && (
            <span style={{ fontSize: 11, color: 'var(--bullish)' }}>
              · {patternLabel(item.triggered_pattern)} on {item.triggered_tf} · {timeAgo(item.triggered_at!)}
            </span>
          )}
          {!triggered && item.expires_at && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              · Expires {timeAgo(item.expires_at).replace('ago', 'left')}
            </span>
          )}
        </div>
      </div>
      <button
        onClick={() => onDelete(item.id)}
        style={{
          width: 28, height: 28, borderRadius: 7, border: 'none', cursor: 'pointer',
          background: 'var(--border)', color: 'var(--text-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
        title="Delete"
      >
        <Trash2 size={12} />
      </button>
    </div>
  )
}


// ── Entry Pattern Alerts tab content ──────────────────────────────────────────

function EntryAlertsPanel({ instruments, prices }: {
  instruments: string[]
  prices?: Record<string, { price: number; updated_at: string }>
}) {
  const [tab, setTab] = useState<'active' | 'history'>('active')
  const [instrument, setInstrument] = useState('')
  const [direction, setDirection] = useState<'bullish' | 'bearish'>('bearish')
  const [price, setPrice] = useState('')
  const [tolerance, setTolerance] = useState('20')
  const [expiry, setExpiry] = useState('1week')
  const [customExpiry, setCustomExpiry] = useState('')
  const [note, setNote] = useState('')
  const [watches, setWatches] = useState<string[]>(ENTRY_DEFAULT_WATCHES)
  const [keepOpen, setKeepOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  const { data: entryData, mutate: mutateEntry } = useSWR<EntryAlertsList>(
    `/api/entry-alerts?tab=${tab}`, fetcher, { refreshInterval: 30000 }
  )

  useEffect(() => {
    if (instruments.length > 0 && !instrument) {
      setInstrument(instruments[0].replace('/', ''))
    }
  }, [instruments, instrument])

  const currentPrice: number | undefined = instrument ? prices?.[instrument]?.price : undefined

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    const priceVal = parseFloat(price)
    const tolVal = tolerance.trim() === '' ? 20 : parseFloat(tolerance)   // optional: blank = the default 20 pips
    if (!instrument || isNaN(priceVal) || priceVal <= 0) {
      setFormError('Select an instrument and enter a valid price.')
      return
    }
    if (watches.length === 0) {
      setFormError('Tick at least one formation to watch on this level.')
      return
    }
    if (isNaN(tolVal) || tolVal <= 0) {
      setFormError('Tolerance has to be at least 1 pip (0 would only fire on the exact price). Leave it empty to use 20 pips.')
      return
    }
    let expiresAt: string | null = null
    if (expiry === 'custom') {
      if (!customExpiry) { setFormError('Choose a custom expiry date.'); return }
      expiresAt = new Date(customExpiry).toISOString()
    } else if (expiry !== 'never') {
      expiresAt = expiryFromPreset(expiry)
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/entry-alerts`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          instrument,
          direction,
          price: priceVal,
          tolerance_pips: tolVal,
          note: note.trim() || null,
          expires_at: expiresAt,
          watches,
          keep_open: keepOpen,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setFormError(err.detail || 'Failed to create alert.')
        return
      }
      setPrice('')
      setNote('')
      setTab('active')
      mutateEntry()
    } catch {
      setFormError('Network error — please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: number) {
    await fetch(`${API_BASE}/api/entry-alerts/${id}`, {
      method: 'DELETE', headers: authHeaders(),
    })
    mutateEntry()
  }

  const activeCount = entryData?.active_count ?? 0
  const maxAlerts = entryData?.max_alerts ?? 20

  return (
    <div className="alert-split">

      {/* ── Create form ─────────────────────────────────────────────── */}
      <div style={{
        background: 'var(--card)', border: '1px solid var(--border)',
        borderRadius: 12, overflow: 'hidden',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={14} color="var(--accent-hover)" />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>New Entry Pattern Alert</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
              Notify me when the formations I pick form at my level
            </div>
          </div>
        </div>

        <form onSubmit={handleCreate} style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 16 }}>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Instrument
            </label>
            <select
              value={instrument}
              onChange={e => setInstrument(e.target.value)}
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text-primary)', outline: 'none',
              }}
            >
              {instruments.map(inst => (
                <option key={inst} value={inst.replace('/', '')}>{inst}</option>
              ))}
            </select>
            {currentPrice !== undefined && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
                Current price: <strong style={{ color: 'var(--text-secondary)' }}>{formatPrice(instrument, currentPrice)}</strong>
              </div>
            )}
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Bias direction
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {([['bullish', 'Buy (bullish)'], ['bearish', 'Sell (bearish)']] as const).map(([val, lbl]) => (
                <button
                  key={val} type="button"
                  onClick={() => setDirection(val as 'bullish' | 'bearish')}
                  style={{
                    padding: '8px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                    border: '1px solid', cursor: 'pointer',
                    borderColor: direction === val ? 'var(--accent)' : 'var(--border)',
                    background: direction === val ? 'var(--accent)' : 'var(--bg)',
                    color: direction === val ? 'white' : 'var(--text-secondary)',
                  }}
                >
                  {lbl}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Price level
            </label>
            <input
              type="number"
              step="any"
              value={price}
              onChange={e => setPrice(e.target.value)}
              placeholder={currentPrice !== undefined ? formatPrice(instrument, currentPrice) : '0.00000'}
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Tolerance (pips) <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· optional</span>
            </label>
            <input
              type="number"
              step="1"
              placeholder="20 (leave empty for the default)"
              value={tolerance}
              onChange={e => setTolerance(e.target.value)}
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
              }}
            />
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
              How close the pattern must form to your level. Default 20 pips covers
              normal overshoots. Use smaller (5-10) for tight levels, larger (30-50)
              for wider zones.
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Formations to watch on this level
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {ENTRY_WATCHES.map(w => {
                const on = watches.includes(w.key)
                return (
                  <label key={w.key} title={w.hint} style={{
                    display: 'flex', alignItems: 'center', gap: 7, padding: '7px 9px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                    border: '1px solid', borderColor: on ? 'var(--accent)' : 'var(--border)',
                    background: on ? 'var(--accent-bg)' : 'var(--bg)', color: 'var(--text-primary)',
                  }}>
                    <input type="checkbox" checked={on}
                      onChange={() => setWatches(on ? watches.filter(x => x !== w.key) : [...watches, w.key])} />
                    {w.label}
                  </label>
                )
              })}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              Each one is checked on its own timeframe, at this level, once the candle has closed. Sweep: a bullish candle wicks below the bearish candle before it and closes back above that low (sells: mirror).
              Sweep and Break: a low (a high for sells) at the level, its sweep, then a close through the last lower high (higher low).
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 10 }}>
              {([[false, 'Close it at the first one'], [true, 'Keep watching the others']] as const).map(([val, lbl]) => (
                <button key={lbl} type="button" onClick={() => setKeepOpen(val)} style={{
                  padding: '7px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500, border: '1px solid', cursor: 'pointer',
                  borderColor: keepOpen === val ? 'var(--accent)' : 'var(--border)',
                  background: keepOpen === val ? 'var(--accent)' : 'var(--bg)',
                  color: keepOpen === val ? 'white' : 'var(--text-secondary)',
                }}>{lbl}</button>
              ))}
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Expires
            </label>
            <select
              value={expiry}
              onChange={e => setExpiry(e.target.value)}
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text-primary)', outline: 'none',
              }}
            >
              <option value="eod">End of day</option>
              <option value="1week">1 week</option>
              <option value="1month">1 month</option>
              <option value="custom">Custom date</option>
              <option value="never">Never</option>
            </select>
            {expiry === 'custom' && (
              <input
                type="date"
                value={customExpiry}
                onChange={e => setCustomExpiry(e.target.value)}
                style={{
                  marginTop: 8, width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                  border: '1px solid var(--border)', background: 'var(--bg)',
                  color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
                }}
              />
            )}
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Note <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
            </label>
            <textarea
              rows={2}
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. Daily Breaker retest from today's SELL BIAS"
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text-primary)', outline: 'none', resize: 'vertical',
                boxSizing: 'border-box', fontFamily: 'inherit',
              }}
            />
          </div>

          {formError && (
            <div style={{ fontSize: 12, color: 'var(--bearish)', padding: '8px 12px', borderRadius: 8, background: 'var(--bearish-bg)' }}>
              {formError}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{
              padding: '10px 16px', borderRadius: 9, fontSize: 13, fontWeight: 600,
              border: 'none', cursor: submitting ? 'not-allowed' : 'pointer',
              background: 'var(--accent)', color: 'white',
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? 'Creating…' : 'Create Entry Alert'}
          </button>

        </form>
      </div>

      {/* ── Alert list ─────────────────────────────────────────────── */}
      <div style={{
        background: 'var(--card)', border: '1px solid var(--border)',
        borderRadius: 12, overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bell size={14} color="var(--accent-hover)" />
            </div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Your Entry Alerts</span>
          </div>
          <span style={{
            fontSize: 12, padding: '3px 10px', borderRadius: 20,
            background: activeCount >= maxAlerts ? 'var(--bearish-bg)' : 'var(--bullish-bg)',
            color: activeCount >= maxAlerts ? 'var(--bearish)' : 'var(--bullish)',
            fontWeight: 600,
          }}>
            {activeCount} of {maxAlerts} active
          </span>
        </div>

        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
          {(['active', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                flex: 1, padding: '11px', fontSize: 13, fontWeight: tab === t ? 600 : 400,
                border: 'none', cursor: 'pointer', background: 'transparent',
                color: tab === t ? 'var(--text-primary)' : 'var(--text-muted)',
                borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              {t === 'active' ? 'Active' : 'History'}
            </button>
          ))}
        </div>

        {!entryData && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Loading…
          </div>
        )}
        {entryData?.items.length === 0 && (
          <div style={{ padding: '40px 24px', textAlign: 'center' }}>
            <Zap size={28} color="var(--text-muted)" style={{ marginBottom: 12 }} />
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', margin: '0 0 4px' }}>
              {tab === 'active' ? 'No active entry alerts' : 'No triggered entry alerts yet'}
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
              {tab === 'active' ? 'Create one using the form.' : 'Triggered alerts appear here.'}
            </p>
          </div>
        )}
        {entryData && entryData.items.length > 0 && (
          <div>
            {entryData.items.map(item => (
              <EntryAlertRow key={item.id} item={item} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}


export default function PriceAlertsPage() {
  const [mainTab, setMainTab] = useState<'price' | 'entry'>('price')
  const [tab, setTab] = useState<'active' | 'history'>('active')

  // Form state
  const [instrument, setInstrument] = useState('')
  const [triggerType, setTriggerType] = useState('on_touch')
  const [timeframe, setTimeframe] = useState('5m')
  const [condition, setCondition] = useState('crossing')
  const [price, setPrice] = useState('')
  const [expiry, setExpiry] = useState('1week')
  const [customExpiry, setCustomExpiry] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  // Data
  const { data: overview } = useSWR<InstrumentOverview[]>('/api/overview', fetcher)
  const { data: prices, mutate: mutatePrices } = useSWR<Record<string, { price: number; updated_at: string }>>(
    '/api/price-alerts/prices', fetcher, { refreshInterval: 60000 }
  )
  const { data: alertsData, mutate: mutateAlerts } = useSWR<PriceAlertsList>(
    `/api/price-alerts?tab=${tab}`, fetcher, { refreshInterval: 30000 }
  )

  // Set default instrument on first load
  useEffect(() => {
    if (overview && overview.length > 0 && !instrument) {
      setInstrument(overview[0].instrument.replace('/', ''))
    }
  }, [overview, instrument])

  const instruments = overview?.map(o => o.instrument) ?? []
  const currentPrice: number | undefined = instrument ? prices?.[instrument]?.price : undefined

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    const priceVal = parseFloat(price)
    if (!instrument || isNaN(priceVal) || priceVal <= 0) {
      setFormError('Select an instrument and enter a valid price.')
      return
    }
    let expiresAt: string | null = null
    if (expiry === 'custom') {
      if (!customExpiry) { setFormError('Choose a custom expiry date.'); return }
      expiresAt = new Date(customExpiry).toISOString()
    } else if (expiry !== 'never') {
      expiresAt = expiryFromPreset(expiry)
    }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/price-alerts`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          instrument,
          trigger_type: triggerType,
          timeframe,
          condition,
          price: priceVal,
          message: message.trim() || null,
          expires_at: expiresAt,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setFormError(err.detail || 'Failed to create alert.')
        return
      }
      // If editing, delete the old alert now that the new one is saved
      if (editingId !== null) {
        await fetch(`${API_BASE}/api/price-alerts/${editingId}`, {
          method: 'DELETE', headers: authHeaders(),
        })
        setEditingId(null)
      }
      setPrice('')
      setMessage('')
      setTab('active')
      mutateAlerts()
    } catch {
      setFormError('Network error — please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function handleEdit(item: PriceAlertItem) {
    setInstrument(item.instrument)
    setTriggerType(item.trigger_type)
    setTimeframe(item.timeframe || '5m')
    setCondition(item.condition)
    setPrice(String(item.price))
    setMessage(item.message ?? '')
    setExpiry('never')
    setCustomExpiry('')
    setFormError('')
    setEditingId(item.id)
    // Scroll form into view
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function handleDelete(id: number) {
    await fetch(`${API_BASE}/api/price-alerts/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (editingId === id) setEditingId(null)
    mutateAlerts()
  }

  const activeCount = alertsData?.active_count ?? 0
  const maxAlerts = alertsData?.max_alerts ?? 20

  return (
    <>
      <TopBar
        title="Level Watch"
        subtitle="Get notified when price hits your level or an entry pattern forms there"
      />
      <main className="page-padded" style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ── Top-level tab switcher ────────────────────────────────── */}
        <div style={{ display: 'inline-flex', gap: 4, background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, alignSelf: 'flex-start' }}>
          {([
            ['price', 'Level Alerts', Target],
            ['entry', 'Entry Pattern Alerts', Zap],
          ] as const).map(([val, lbl, Icon]) => (
            <button
              key={val}
              onClick={() => setMainTab(val)}
              style={{
                padding: '8px 16px', borderRadius: 7, fontSize: 13,
                fontWeight: mainTab === val ? 600 : 500,
                border: 'none', cursor: 'pointer',
                background: mainTab === val ? 'var(--accent)' : 'transparent',
                color: mainTab === val ? 'white' : 'var(--text-secondary)',
                display: 'flex', alignItems: 'center', gap: 6,
                transition: 'all 0.12s',
              }}
            >
              <Icon size={13} />
              {lbl}
            </button>
          ))}
        </div>

        {mainTab === 'entry' ? (
          <EntryAlertsPanel instruments={instruments} prices={prices} />
        ) : (
        <div className="alert-split">

          {/* ── Create form ─────────────────────────────────────────────── */}
          <div style={{
            background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 12, overflow: 'hidden',
          }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Target size={14} color="var(--accent-hover)" />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{editingId ? 'Edit Alert' : 'New Price Alert'}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
                  {editingId ? 'Modify the alert — old one will be replaced' : 'Notify me when price reaches a level'}
                </div>
              </div>
              {editingId && (
                <button
                  type="button"
                  onClick={() => { setEditingId(null); setPrice(''); setMessage('') }}
                  style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  Cancel
                </button>
              )}
            </div>

            <form onSubmit={handleCreate} style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* Pair */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Instrument
                </label>
                <select
                  value={instrument}
                  onChange={e => setInstrument(e.target.value)}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    border: '1px solid var(--border)', background: 'var(--bg)',
                    color: 'var(--text-primary)', outline: 'none',
                  }}
                >
                  {instruments.map(inst => (
                    <option key={inst} value={inst.replace('/', '')}>{inst}</option>
                  ))}
                </select>
                {currentPrice !== undefined && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Clock size={10} />
                    Current price: <strong style={{ color: 'var(--text-secondary)' }}>{formatPrice(instrument, currentPrice)}</strong>
                    {prices?.[instrument]?.updated_at && (
                      <span>· {timeAgo(prices[instrument].updated_at)}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Trigger */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Trigger
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  {[['on_touch', 'On touch'], ['on_candle_close', 'On candle close']].map(([val, lbl]) => (
                    <button
                      key={val} type="button"
                      onClick={() => setTriggerType(val)}
                      style={{
                        padding: '8px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                        border: '1px solid', cursor: 'pointer',
                        borderColor: triggerType === val ? 'var(--accent)' : 'var(--border)',
                        background: triggerType === val ? 'var(--accent)' : 'var(--bg)',
                        color: triggerType === val ? 'white' : 'var(--text-secondary)',
                        transition: 'all 0.12s',
                      }}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Timeframe — only for candle close */}
              {triggerType === 'on_candle_close' && (
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                    Timeframe
                  </label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {['5m', '15m', '30m', '45m', '1h', '2h', '3h', '4h', '1D', '1W'].map(tf => (
                      <button
                        key={tf} type="button"
                        onClick={() => setTimeframe(tf)}
                        style={{
                          padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                          border: '1px solid', cursor: 'pointer',
                          borderColor: timeframe === tf ? 'var(--accent)' : 'var(--border)',
                          background: timeframe === tf ? 'var(--accent)' : 'var(--bg)',
                          color: timeframe === tf ? 'white' : 'var(--text-secondary)',
                          transition: 'all 0.12s',
                        }}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Condition */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Condition
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {[['crossing', 'Crossing (either direction)'], ['crossing_up', 'Crossing up'], ['crossing_down', 'Crossing down'], ['rejects', 'Rejects level (wick + close back)']].map(([val, lbl]) => (
                    <button
                      key={val} type="button"
                      onClick={() => setCondition(val)}
                      style={{
                        padding: '8px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                        border: '1px solid', cursor: 'pointer', textAlign: 'left',
                        borderColor: condition === val ? 'var(--accent)' : 'var(--border)',
                        background: condition === val ? 'var(--accent)' : 'var(--bg)',
                        color: condition === val ? 'white' : 'var(--text-secondary)',
                        transition: 'all 0.12s',
                      }}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Price
                </label>
                <input
                  type="number"
                  step="any"
                  value={price}
                  onChange={e => setPrice(e.target.value)}
                  placeholder={currentPrice !== undefined ? formatPrice(instrument, currentPrice) : '0.00000'}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    border: '1px solid var(--border)', background: 'var(--bg)',
                    color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
                  }}
                />
              </div>

              {/* Alert preview */}
              {(() => {
                const preview = alertPreview(instrument, triggerType, timeframe, condition, price, currentPrice)
                if (!preview) return null
                return (
                  <div style={{
                    fontSize: 12, color: 'var(--text-secondary)',
                    background: 'var(--bg)', border: '1px solid var(--border)',
                    borderRadius: 8, padding: '10px 12px', lineHeight: 1.6,
                  }}>
                    {preview}
                  </div>
                )
              })()}

              {/* Expires */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Expires
                </label>
                <select
                  value={expiry}
                  onChange={e => setExpiry(e.target.value)}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    border: '1px solid var(--border)', background: 'var(--bg)',
                    color: 'var(--text-primary)', outline: 'none',
                  }}
                >
                  <option value="eod">End of day</option>
                  <option value="1week">1 week</option>
                  <option value="1month">1 month</option>
                  <option value="custom">Custom date</option>
                  <option value="never">Never</option>
                </select>
                {expiry === 'custom' && (
                  <input
                    type="date"
                    value={customExpiry}
                    onChange={e => setCustomExpiry(e.target.value)}
                    style={{
                      marginTop: 8, width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                      border: '1px solid var(--border)', background: 'var(--bg)',
                      color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                )}
              </div>

              {/* Message */}
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Message <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
                </label>
                <textarea
                  rows={2}
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  placeholder="e.g. EURUSD breaker retest — check for entry"
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    border: '1px solid var(--border)', background: 'var(--bg)',
                    color: 'var(--text-primary)', outline: 'none', resize: 'vertical',
                    boxSizing: 'border-box', fontFamily: 'inherit',
                  }}
                />
              </div>

              {formError && (
                <div style={{ fontSize: 12, color: 'var(--bearish)', padding: '8px 12px', borderRadius: 8, background: 'var(--bearish-bg)' }}>
                  {formError}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: '10px 16px', borderRadius: 9, fontSize: 13, fontWeight: 600,
                  border: 'none', cursor: submitting ? 'not-allowed' : 'pointer',
                  background: 'var(--accent)', color: 'white',
                  opacity: submitting ? 0.6 : 1,
                  transition: 'opacity 0.1s',
                }}
              >
                {submitting ? (editingId ? 'Updating…' : 'Creating…') : (editingId ? 'Update Alert' : 'Create Alert')}
              </button>

            </form>
          </div>

          {/* ── Alert list ─────────────────────────────────────────────── */}
          <div style={{
            background: 'var(--card)', border: '1px solid var(--border)',
            borderRadius: 12, overflow: 'hidden',
          }}>
            <div style={{
              padding: '16px 20px', borderBottom: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Bell size={14} color="var(--accent-hover)" />
                </div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>Your Alerts</span>
              </div>
              <span style={{
                fontSize: 12, padding: '3px 10px', borderRadius: 20,
                background: activeCount >= maxAlerts ? 'var(--bearish-bg)' : 'var(--bullish-bg)',
                color: activeCount >= maxAlerts ? 'var(--bearish)' : 'var(--bullish)',
                fontWeight: 600,
              }}>
                {activeCount} of {maxAlerts} active
              </span>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
              {(['active', 'history'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1, padding: '11px', fontSize: 13, fontWeight: tab === t ? 600 : 400,
                    border: 'none', cursor: 'pointer', background: 'transparent',
                    color: tab === t ? 'var(--text-primary)' : 'var(--text-muted)',
                    borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
                    transition: 'color 0.12s',
                  }}
                >
                  {t === 'active' ? 'Active' : 'History'}
                </button>
              ))}
            </div>

            {/* Items */}
            {!alertsData && (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                Loading…
              </div>
            )}
            {alertsData?.items.length === 0 && (
              <div style={{ padding: '40px 24px', textAlign: 'center' }}>
                <Target size={28} color="var(--text-muted)" style={{ marginBottom: 12 }} />
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', margin: '0 0 4px' }}>
                  {tab === 'active' ? 'No active alerts' : 'No triggered alerts yet'}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                  {tab === 'active' ? 'Create one using the form.' : 'Triggered alerts appear here.'}
                </p>
              </div>
            )}
            {alertsData && alertsData.items.length > 0 && (
              <div>
                {alertsData.items.map(item => (
                  <AlertRow key={item.id} item={item} onDelete={handleDelete} onEdit={handleEdit} />
                ))}
              </div>
            )}
          </div>

        </div>
        )}

        {/* Note about price updates */}
        <div style={{
          fontSize: 12, color: 'var(--text-muted)', padding: '10px 14px',
          borderRadius: 8, background: 'var(--card)', border: '1px solid var(--border)',
          display: 'flex', alignItems: 'flex-start', gap: 8,
        }}>
          <Clock size={13} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            {mainTab === 'entry'
              ? 'Entry Pattern alerts fire when a formation you picked (H1 / H2 Sweep, M15 / M5 Sweep and Break, or PCL) forms within tolerance of your level in your direction. The first one closes the alert, unless you chose to keep watching the others.'
              : 'On touch alerts fire within 5 minutes of the level being crossed. Candle close alerts fire only at the close of your chosen timeframe candle.'}
          </span>
        </div>

      </main>
    </>
  )
}
