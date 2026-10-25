// Opened from the bot's Mini App buttons: Telegram puts the signed launch data
// in the URL hash (#tgWebAppData=…). We keep it for this tab so moving between
// pages still knows it's inside Telegram, and load Telegram's script to size
// the page and theme the header.

const KEY = 'mbp_tg_init'

declare global {
  interface Window {
    Telegram?: { WebApp?: { initData?: string; ready: () => void; expand: () => void; setHeaderColor?: (c: string) => void
      BackButton?: { show: () => void; hide: () => void; onClick: (f: () => void) => void; offClick: (f: () => void) => void } } }
  }
}

export function telegramInitData(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const fromHash = new URLSearchParams(window.location.hash.slice(1)).get('tgWebAppData')
    if (fromHash) {
      sessionStorage.setItem(KEY, fromHash)
      return fromHash
    }
    return window.Telegram?.WebApp?.initData || sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function startTelegramApp(): void {
  if (typeof document === 'undefined' || document.getElementById('tg-webapp')) return
  const s = document.createElement('script')
  s.id = 'tg-webapp'
  s.src = 'https://telegram.org/js/telegram-web-app.js'
  s.onload = () => {
    const wa = window.Telegram?.WebApp
    if (!wa) return
    wa.ready()
    wa.expand()
    try {
      const bg = getComputedStyle(document.body).backgroundColor
      if (bg && wa.setHeaderColor) wa.setHeaderColor(rgbToHex(bg))
    } catch {}
  }
  document.head.appendChild(s)
}

function rgbToHex(rgb: string): string {
  const m = rgb.match(/\d+/g)
  if (!m || m.length < 3) return '#090A14'
  return '#' + m.slice(0, 3).map(n => Number(n).toString(16).padStart(2, '0')).join('')
}
