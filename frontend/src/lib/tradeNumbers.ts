// The journal's own count. A new month starts again at 1, the year keeps going. A setup entered more than once holds
// that many numbers: a stop-out and a re-entry on the 24th and 25th trades of the year reads "24, 25".
// Everything is counted, whatever filter is on, so filtering never changes a number.

export interface TradeNum { month: string; year: string }   // "5, 6" and "24, 25"
export const NO_NUM: TradeNum = { month: '', year: '' }

interface Numbered {
  id: number
  trade_date: string
  results: Record<string, { outcome: string; takes?: number }>
}

// Rows on one setup test different ways into the same move, so the setup counts its biggest "times entered", not their sum
export function timesEntered(t: Numbered): number {
  const counts = Object.values(t.results || {}).filter(r => r.outcome !== 'none').map(r => r.takes ?? 1)
  return Math.max(1, ...counts)
}

export function numberTrades(trades: Numbered[]): Map<number, TradeNum> {
  const seen = new Map<string, number>()
  const next = (key: string, count: number) => {
    const from = seen.get(key) ?? 0
    seen.set(key, from + count)
    return Array.from({ length: count }, (_, i) => from + i + 1).join(', ')
  }
  const inOrder = [...trades].sort((a, b) => a.trade_date.localeCompare(b.trade_date) || a.id - b.id)
  return new Map(inOrder.map(t => {
    const count = timesEntered(t)
    return [t.id, { month: next(t.trade_date.slice(0, 7), count), year: next(t.trade_date.slice(0, 4), count) }]
  }))
}

export const tradesWord = (num: string) => (num.includes(',') ? 'trades' : 'trade')
