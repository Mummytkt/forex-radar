'use client'
import { useEffect, useState } from 'react'

// Notification-list filter (dashboard Latest Notifications + Signal Log): which
// alert types to show. Remembered in this browser (mbp_alert_types); empty = all.
// Telegram delivery is set separately in Alert Filters.
export const ALERT_TYPES: { key: string; label: string }[] = [
  { key: 'origin', label: 'Origin' },
  { key: 'daily_react', label: 'Daily reaction + H4' },
  { key: 'realign', label: 'Back in line' },
  { key: 'inline', label: 'H4 in line' },
  { key: 'breaker', label: 'H4 Breaker' },
  { key: 'oc', label: 'H4 OC' },
  { key: 'engulfing', label: 'H4 engulfing' },
  { key: 'd_engulfing', label: 'Daily engulfing' },
  { key: 'h4_fvg', label: 'H4 FVG' },
]
export const typeLabel = (k?: string) => ALERT_TYPES.find(t => t.key === k)?.label ?? 'Origin'

const KEY = 'mbp_alert_types'
const EVT = 'mbp-alert-types'

export function useAlertTypes(): [string[], (t: string[]) => void] {
  const [types, setTypes] = useState<string[]>([])
  useEffect(() => {
    const load = () => {
      try {
        const v = JSON.parse(localStorage.getItem(KEY) || '[]')
        setTypes(Array.isArray(v) ? v.filter((k: string) => ALERT_TYPES.some(t => t.key === k)) : [])
      } catch { setTypes([]) }
    }
    load()
    window.addEventListener(EVT, load)
    return () => window.removeEventListener(EVT, load)
  }, [])
  const save = (t: string[]) => {
    setTypes(t)
    try { localStorage.setItem(KEY, JSON.stringify(t)) } catch { /* private mode */ }
    window.dispatchEvent(new Event(EVT))
  }
  return [types, save]
}

// The ?types= part of /api/alerts for the current choice ('' = all)
export const typesQuery = (types: string[]) => (types.length ? `&types=${types.join(',')}` : '')

export default function AlertTypeFilter({ types, onChange, compact }: { types: string[]; onChange: (t: string[]) => void; compact?: boolean }) {
  const chip = (on: boolean) => ({
    padding: compact ? '4px 10px' : '6px 12px', borderRadius: 999, fontSize: compact ? 11 : 12, fontWeight: 600,
    border: '1px solid', cursor: 'pointer', transition: 'all 0.12s',
    borderColor: on ? 'var(--accent)' : 'var(--border)',
    background: on ? 'var(--accent)' : 'var(--card)',
    color: on ? 'white' : 'var(--text-secondary)',
  } as const)
  const toggle = (k: string) => onChange(types.includes(k) ? types.filter(t => t !== k) : [...types, k])
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }} role="group" aria-label="Filter by alert type">
      <button onClick={() => onChange([])} style={chip(types.length === 0)}>All types</button>
      {ALERT_TYPES.map(t => (
        <button key={t.key} onClick={() => toggle(t.key)} style={chip(types.includes(t.key))} aria-pressed={types.includes(t.key)}>
          {t.label}
        </button>
      ))}
    </div>
  )
}
