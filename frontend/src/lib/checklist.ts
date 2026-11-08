// The Checklist journal's tick boxes. Keys are stored, so never rename one; must match CHECK_ITEMS in
// api/entry_tests.py. The labels are the owner's own words.
export const CHECK_ITEMS: { key: string; label: string }[] = [
  { key: 'h4_liq', label: 'H4 Liquidity?' },
  { key: 'h1_liq_only', label: 'H1 Liquidity only?' },
  { key: 'octgd_1h', label: '1hr OCTGD?' },
  { key: 'cisd_1h', label: '1hr CISD' },
  { key: 'sl_kl_poi', label: 'SL behind KL POI?' },
  { key: 'sl_1h_candle', label: 'SL behind 1hr candle?' },
  { key: 'kl_reaction', label: 'Reaction from an actual key level in the POI?' },
]
export const CHECK_RATIOS = [1, 2, 3]
export interface Checklist { items: string[]; ratio: number | null }
export const EMPTY_CHECKLIST: Checklist = { items: [], ratio: null }

// How often each box was ticked over some trades, and how often each ratio was reached: the consistency count
export function checklistCounts(lists: (Checklist | undefined)[]) {
  const n = lists.length
  const items = CHECK_ITEMS.map(i => ({ ...i, count: lists.filter(c => c?.items?.includes(i.key)).length }))
  const ratios = CHECK_RATIOS.map(r => ({ r, count: lists.filter(c => c?.ratio === r).length }))
  return { n, items, ratios, noRatio: n - ratios.reduce((s, x) => s + x.count, 0) }
}

// The same count as one line of words, for the book: "H4 Liquidity? 5 of 6 · … · Highest ratio done: 1R ×2, 2R ×3"
export function checklistLine(lists: (Checklist | undefined)[]): string {
  const c = checklistCounts(lists)
  const ratios = c.ratios.filter(x => x.count).map(x => `${x.r}R ×${x.count}`)
  return `Checklist: ${c.items.map(i => `${i.label} ${i.count} of ${c.n}`).join(' · ')} · Highest ratio done: ${ratios.length ? ratios.join(', ') : 'none ticked'}`
}
