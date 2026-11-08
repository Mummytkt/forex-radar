// The Checklist journal's tick boxes. Keys are stored, so never rename one; must match CHECK_ITEMS in
// api/entry_tests.py. The labels are the owner's own words.
export const CHECK_ITEMS: { key: string; label: string }[] = [
  { key: 'h4_liq', label: 'H4 Liquidity' },
  { key: 'h1_liq_only', label: 'H1 Liquidity only' },
  { key: 'sl_kl_poi', label: 'SL behind KL POI' },
  { key: 'sl_1h_candle', label: 'SL behind 1hr candle' },
  { key: 'kl_reaction', label: 'Reaction from an actual key level in the POI' },
]
// 1hr OCTGD (octgd_1h) and 1hr CISD (cisd_1h) were taken off on 2026-11-08: they are entry types now. Ticks
// already saved on them stay stored but aren't shown.
export const CHECK_RATIOS = [1, 2, 3]
export interface Checklist { items: string[]; ratio: number | null }
export const EMPTY_CHECKLIST: Checklist = { items: [], ratio: null }

