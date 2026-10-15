export type State = 'IDLE' | 'BREAKOUT_ACTIVE' | 'RETEST_IN_PROGRESS'
export type Direction = 'BULLISH' | 'BEARISH'

export interface InstrumentOverview {
  instrument: string
  state: State
  direction: Direction | null           // Daily breakout direction — setup in progress
  last_alert_direction: Direction | null // Confirmed bias — only present after alert fires
  breakout_level: number | null
  breakout_ts: string | null
  last_alert_at: string | null
  active_sources_count: number
  last_updated: string | null
  category: string
}

export interface Stats {
  total_instruments: number
  active_breakouts: number
  retests_in_progress: number
  alerts_today: number
  total_alerts: number
}

export interface AlertItem {
  id: number
  instrument: string
  direction: Direction
  source_type: string
  h4_classification: string
  alert_classification: string
  alert_text: string
  fired_at: string
}

export interface AlertsPage {
  items: AlertItem[]
  total: number
}

export interface ActiveSource {
  source_type: string
  direction: string
  level: number
  band_low: number
  band_high: number
  created_at: string
}

export interface InstrumentDetail {
  overview: InstrumentOverview
  active_sources: ActiveSource[]
  recent_alerts: AlertItem[]
}

export interface PriceAlertItem {
  id: number
  instrument: string
  trigger_type: string
  timeframe: string
  condition: string
  price: number
  message: string | null
  expires_at: string | null
  is_active: boolean
  triggered_at: string | null
  created_at: string
}

export interface PriceAlertsList {
  items: PriceAlertItem[]
  active_count: number
  max_alerts: number
}

export interface EntryAlertItem {
  id: number
  instrument: string
  direction: string            // 'bullish' | 'bearish'
  price: number
  tolerance_pips: number
  note: string | null
  expires_at: string | null
  is_active: boolean
  triggered_at: string | null
  triggered_pattern: string | null  // 'pcl' | 'engulfing_sweep'
  triggered_tf: string | null       // 'H1' | 'H2'
  created_at: string
}

export interface EntryAlertsList {
  items: EntryAlertItem[]
  active_count: number
  max_alerts: number
}
