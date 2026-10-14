export interface AccentSwatch {
  id: string
  name: string
  color: string
  dark: {
    accent: string; hover: string; bg: string
    pageBg: string; surface: string; card: string; cardHover: string
    border: string; borderBright: string
  }
  light: {
    accent: string; hover: string; bg: string
    pageBg: string; surface: string; card: string; cardHover: string
    border: string; borderBright: string
  }
}

export const PALETTE: AccentSwatch[] = [
  {
    id: 'indigo', name: 'Indigo', color: '#6366F1',
    dark:  { accent: '#6366F1', hover: '#818CF8', bg: 'rgba(99,102,241,0.12)',
             pageBg: '#090A14', surface: '#0F1120', card: '#131526', cardHover: '#181A30', border: '#1C1E35', borderBright: '#272A48' },
    light: { accent: '#4F46E5', hover: '#4338CA', bg: 'rgba(79,70,229,0.09)',
             pageBg: '#EFF1FB', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F5F7FF', border: '#DDE1EF', borderBright: '#C8CEEA' },
  },
  {
    id: 'emerald', name: 'Emerald', color: '#10B981',
    dark:  { accent: '#10B981', hover: '#34D399', bg: 'rgba(16,185,129,0.12)',
             pageBg: '#050F09', surface: '#091A0F', card: '#0C2014', cardHover: '#0F2719', border: '#122C1E', borderBright: '#1A402C' },
    light: { accent: '#059669', hover: '#047857', bg: 'rgba(5,150,105,0.09)',
             pageBg: '#F0FAF5', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F3FBF7', border: '#C6E9D8', borderBright: '#A8D9C2' },
  },
  {
    id: 'sky', name: 'Sky', color: '#0EA5E9',
    dark:  { accent: '#0EA5E9', hover: '#38BDF8', bg: 'rgba(14,165,233,0.12)',
             pageBg: '#050C13', surface: '#09141F', card: '#0B1A28', cardHover: '#0E2130', border: '#112638', borderBright: '#1A384E' },
    light: { accent: '#0284C7', hover: '#0369A1', bg: 'rgba(2,132,199,0.09)',
             pageBg: '#EFF8FF', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F2F9FF', border: '#C5DFF0', borderBright: '#A4CCDF' },
  },
  {
    id: 'purple', name: 'Purple', color: '#A855F7',
    dark:  { accent: '#A855F7', hover: '#C084FC', bg: 'rgba(168,85,247,0.12)',
             pageBg: '#0C0912', surface: '#150E1C', card: '#1B1224', cardHover: '#22162D', border: '#291A36', borderBright: '#3C264E' },
    light: { accent: '#9333EA', hover: '#7E22CE', bg: 'rgba(147,51,234,0.09)',
             pageBg: '#F5F0FF', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F9F5FF', border: '#DDC8F0', borderBright: '#C9ABE5' },
  },
  {
    id: 'amber', name: 'Amber', color: '#F59E0B',
    dark:  { accent: '#F59E0B', hover: '#FCD34D', bg: 'rgba(245,158,11,0.12)',
             pageBg: '#120E05', surface: '#1D1609', card: '#251C0B', cardHover: '#2D220E', border: '#362811', borderBright: '#4D3A18' },
    light: { accent: '#D97706', hover: '#B45309', bg: 'rgba(217,119,6,0.09)',
             pageBg: '#FFFBF0', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#FFFDF5', border: '#EFD898', borderBright: '#E0C070' },
  },
  {
    id: 'rose', name: 'Rose', color: '#FB7185',
    dark:  { accent: '#FB7185', hover: '#FDA4AF', bg: 'rgba(251,113,133,0.12)',
             pageBg: '#120608', surface: '#1E0B0F', card: '#260E14', cardHover: '#2E1119', border: '#38141F', borderBright: '#501D2C' },
    light: { accent: '#E11D48', hover: '#BE123C', bg: 'rgba(225,29,72,0.09)',
             pageBg: '#FFF0F3', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#FFF5F7', border: '#F0C0CA', borderBright: '#E0A0B0' },
  },
  {
    id: 'cyan', name: 'Cyan', color: '#06B6D4',
    dark:  { accent: '#06B6D4', hover: '#22D3EE', bg: 'rgba(6,182,212,0.12)',
             pageBg: '#04100F', surface: '#081B1A', card: '#0A2221', cardHover: '#0D2A29', border: '#103130', borderBright: '#184644' },
    light: { accent: '#0891B2', hover: '#0E7490', bg: 'rgba(8,145,178,0.09)',
             pageBg: '#EDFAFD', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#F2FBFE', border: '#B8E4ED', borderBright: '#90D0DF' },
  },
  {
    id: 'orange', name: 'Orange', color: '#F97316',
    dark:  { accent: '#F97316', hover: '#FB923C', bg: 'rgba(249,115,22,0.12)',
             pageBg: '#120A04', surface: '#1D1108', card: '#25160A', cardHover: '#2D1B0D', border: '#362010', borderBright: '#4D2E17' },
    light: { accent: '#EA580C', hover: '#C2410C', bg: 'rgba(234,88,12,0.09)',
             pageBg: '#FFF7F0', surface: '#FFFFFF', card: '#FFFFFF', cardHover: '#FFFAF5', border: '#F0D0B0', borderBright: '#E0B888' },
  },
]

export const DEFAULT_ACCENT = 'indigo'

export function applyAccent(swatchId: string, theme: 'dark' | 'light') {
  const swatch = PALETTE.find(s => s.id === swatchId) ?? PALETTE[0]
  const v = theme === 'dark' ? swatch.dark : swatch.light
  const root = document.documentElement
  root.style.setProperty('--accent', v.accent)
  root.style.setProperty('--accent-hover', v.hover)
  root.style.setProperty('--accent-bg', v.bg)
  root.style.setProperty('--bg', v.pageBg)
  root.style.setProperty('--surface', v.surface)
  root.style.setProperty('--card', v.card)
  root.style.setProperty('--card-hover', v.cardHover)
  root.style.setProperty('--border', v.border)
  root.style.setProperty('--border-bright', v.borderBright)
  try { localStorage.setItem('mbp_accent', swatchId) } catch {}
}
