export type State = 'IDLE' | 'BREAKOUT_ACTIVE' | 'RETEST_IN_PROGRESS'
export type Direction = 'BULLISH' | 'BEARISH'

export interface InstrumentOverview {
  instrument: string
  state: State
  direction: Direction | null
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
