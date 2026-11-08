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
  const n = Object.values(t.results || {}).filter(r => r.outcome !== 'none').map(r => r.takes ?? 1)
  return Math.max(1, ...n)
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

// Every entry on a result: each one before the last was stopped out, so it is a loss; the last is the result ticked
export function entriesIn(r: { outcome: string; takes?: number }): { w: number; l: number; be: number } {
  if (r.outcome === 'none') return { w: 0, l: 0, be: 0 }
  const before = Math.max((r.takes ?? 1) - 1, 0)
  return { w: r.outcome === 'win' ? 1 : 0, l: before + (r.outcome === 'loss' ? 1 : 0), be: r.outcome === 'be' ? 1 : 0 }
}

// Win / loss streaks over every entry, oldest to newest. A BE or no entry is skipped (it doesn't end a streak).
// now = the run still going at the newest entry.
export function streaks(seq: { o: string; takes?: number }[]) {
  let run = 0, runO: string | null = null, bestW = 0, worstL = 0
  const step = (o: string) => {
    if (o === runO) run++
    else { runO = o; run = 1 }
    if (o === 'win') bestW = Math.max(bestW, run)
    else worstL = Math.max(worstL, run)
  }
  for (const x of seq) {
    if (x.o === 'none') continue
    const { w, l } = entriesIn({ outcome: x.o, takes: x.takes })
    for (let i = 0; i < l; i++) step('loss')
    if (w) step('win')
  }
  return { now: run, nowO: runO, bestW, worstL }
}

export const tradesWord = (num: string) => (num.includes(',') ? 'trades' : 'trade')
