// The Checklist journal's tick boxes. Keys are stored, so never rename one; must match CHECK_ITEMS in
// api/entry_tests.py. The labels are the owner's own words.
// says: how the diary page writes it out when ticked
export const CHECK_ITEMS: { key: string; label: string; says: string }[] = [
  { key: 'h4_liq', label: 'H4 Liquidity', says: 'there was H4 liquidity' },
  { key: 'h1_liq_only', label: 'H1 Liquidity', says: 'there was H1 liquidity' },   // key kept from "H1 Liquidity only"
  { key: 'mtf_poi', label: 'H4 POI', says: 'there was a H4 POI' },   // first named MTF POI
  { key: 'ltf_poi', label: 'H1 POI', says: 'there was a H1 POI' },   // first named LTF POI
]
// Taken off on 2026-11-09: SL behind KL POI (sl_kl_poi), SL behind 1hr candle (sl_1h_candle), Reaction from an actual
// key level in the POI (kl_reaction). Ticks already saved on them stay stored but aren't shown.
// 1hr OCTGD (octgd_1h) and 1hr CISD (cisd_1h) were taken off on 2026-11-08: they are entry types now. Ticks
// already saved on them stay stored but aren't shown.
export const CHECK_RATIOS = [1, 2, 3]
export interface Checklist { items: string[]; ratio: number | null }
export const EMPTY_CHECKLIST: Checklist = { items: [], ratio: null }

// Only what was ticked, as words: "On my checklist, there was H4 liquidity and my stop loss was behind the KL POI.
// The highest ratio done was 2R." Nothing ticked: ''
export function checklistText(c: Checklist): string {
  const said = CHECK_ITEMS.filter(i => c.items?.includes(i.key)).map(i => i.says)
  const list = said.length <= 1 ? said.join('') : `${said.slice(0, -1).join(', ')} and ${said[said.length - 1]}`
  const parts: string[] = []
  if (list) parts.push(`On my checklist, ${list}.`)
  if (c.ratio) parts.push(`The highest ratio done was ${c.ratio}R.`)
  return parts.join(' ')
}

