export interface UserPreferences {
  enabledPairs: string[]   // empty = all enabled
  alertExternal: boolean
  alertInternal: boolean
  direction: 'ALL' | 'BULLISH' | 'BEARISH'
}

const DEFAULTS: UserPreferences = {
  enabledPairs: [],
  alertExternal: true,
  alertInternal: false,
  direction: 'ALL',
}

const PREFS_KEY = 'mbp_prefs'
const NAME_KEY = 'mbp_name'

export function loadPrefs(): UserPreferences {
  if (typeof window === 'undefined') return DEFAULTS
  try {
    const raw = localStorage.getItem(PREFS_KEY) ?? localStorage.getItem('biasradar_prefs')
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { return DEFAULTS }
}

export function savePrefs(p: UserPreferences) {
  if (typeof window === 'undefined') return
  localStorage.setItem(PREFS_KEY, JSON.stringify(p))
}

export function loadUserName(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(NAME_KEY) ?? localStorage.getItem('biasradar_name') ?? ''
}

export function saveUserName(name: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(NAME_KEY, name)
}
