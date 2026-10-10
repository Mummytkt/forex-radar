import { formatDistanceToNow, parseISO } from 'date-fns'
import type { State, Direction } from './types'

export function timeAgo(iso: string | null): string {
  if (!iso) return '—'
  try { return formatDistanceToNow(parseISO(iso), { addSuffix: true }) }
  catch { return '—' }
}

export function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('en-GB', { timeZone: 'UTC', dateStyle: 'medium', timeStyle: 'short' }) + ' UTC' }
  catch { return '—' }
}

export function stateLabel(state: State): string {
  return { IDLE: 'Idle', BREAKOUT_ACTIVE: 'Breakout Active', RETEST_IN_PROGRESS: 'Retest In Progress' }[state]
}

export function stateColor(state: State): string {
  return {
    IDLE: 'text-[var(--text-secondary)]',
    BREAKOUT_ACTIVE: 'text-[var(--accent)]',
    RETEST_IN_PROGRESS: 'text-[var(--retest)]',
  }[state]
}

export function stateBorder(state: State): string {
  return {
    IDLE: 'border-l-[var(--border)]',
    BREAKOUT_ACTIVE: 'border-l-[var(--accent)]',
    RETEST_IN_PROGRESS: 'border-l-[var(--retest)]',
  }[state]
}

export function directionColor(dir: Direction | null): string {
  if (!dir) return 'text-[var(--text-secondary)]'
  return dir === 'BULLISH' ? 'text-[var(--bullish)]' : 'text-[var(--bearish)]'
}

export function sourceTypeLabel(t: string): string {
  return {
    DAILY_BREAKER: 'Daily Breaker',
    OC_INSIDE_RANGE: 'OC Inside Range',
    AV_INSIDE_RANGE: 'A/V Key Level',
    POST_BREAKOUT_DAILY_OC: 'Post-Breakout OC',
    UNKNOWN: 'Unknown',
  }[t] ?? t
}

export function isForexOpen(): boolean {
  const now = new Date()
  const wd = now.getUTCDay() // 0=Sun, 5=Fri, 6=Sat
  const h = now.getUTCHours()
  if (wd === 6) return false
  if (wd === 5 && h >= 22) return false
  if (wd === 0 && h < 22) return false
  return true
}
