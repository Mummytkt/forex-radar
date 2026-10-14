export interface AccentSwatch {
  id: string
  name: string
  color: string  // preview swatch color (dark variant)
  dark: { accent: string; hover: string; bg: string }
  light: { accent: string; hover: string; bg: string }
}

export const PALETTE: AccentSwatch[] = [
  {
    id: 'indigo', name: 'Indigo', color: '#6366F1',
    dark:  { accent: '#6366F1', hover: '#818CF8', bg: 'rgba(99,102,241,0.12)' },
    light: { accent: '#4F46E5', hover: '#4338CA', bg: 'rgba(79,70,229,0.09)' },
  },
  {
    id: 'emerald', name: 'Emerald', color: '#10B981',
    dark:  { accent: '#10B981', hover: '#34D399', bg: 'rgba(16,185,129,0.12)' },
    light: { accent: '#059669', hover: '#047857', bg: 'rgba(5,150,105,0.09)' },
  },
  {
    id: 'sky', name: 'Sky', color: '#0EA5E9',
    dark:  { accent: '#0EA5E9', hover: '#38BDF8', bg: 'rgba(14,165,233,0.12)' },
    light: { accent: '#0284C7', hover: '#0369A1', bg: 'rgba(2,132,199,0.09)' },
  },
  {
    id: 'purple', name: 'Purple', color: '#A855F7',
    dark:  { accent: '#A855F7', hover: '#C084FC', bg: 'rgba(168,85,247,0.12)' },
    light: { accent: '#9333EA', hover: '#7E22CE', bg: 'rgba(147,51,234,0.09)' },
  },
  {
    id: 'amber', name: 'Amber', color: '#F59E0B',
    dark:  { accent: '#F59E0B', hover: '#FCD34D', bg: 'rgba(245,158,11,0.12)' },
    light: { accent: '#D97706', hover: '#B45309', bg: 'rgba(217,119,6,0.09)' },
  },
  {
    id: 'rose', name: 'Rose', color: '#FB7185',
    dark:  { accent: '#FB7185', hover: '#FDA4AF', bg: 'rgba(251,113,133,0.12)' },
    light: { accent: '#E11D48', hover: '#BE123C', bg: 'rgba(225,29,72,0.09)' },
  },
  {
    id: 'cyan', name: 'Cyan', color: '#06B6D4',
    dark:  { accent: '#06B6D4', hover: '#22D3EE', bg: 'rgba(6,182,212,0.12)' },
    light: { accent: '#0891B2', hover: '#0E7490', bg: 'rgba(8,145,178,0.09)' },
  },
  {
    id: 'orange', name: 'Orange', color: '#F97316',
    dark:  { accent: '#F97316', hover: '#FB923C', bg: 'rgba(249,115,22,0.12)' },
    light: { accent: '#EA580C', hover: '#C2410C', bg: 'rgba(234,88,12,0.09)' },
  },
]

export const DEFAULT_ACCENT = 'indigo'

export function applyAccent(swatchId: string, theme: 'dark' | 'light') {
  const swatch = PALETTE.find(s => s.id === swatchId) ?? PALETTE[0]
  const vars = theme === 'dark' ? swatch.dark : swatch.light
  const root = document.documentElement
  root.style.setProperty('--accent', vars.accent)
  root.style.setProperty('--accent-hover', vars.hover)
  root.style.setProperty('--accent-bg', vars.bg)
  try { localStorage.setItem('mbp_accent', swatchId) } catch {}
}

// Serialised palette for the FOUC-prevention inline script in layout.tsx
export const PALETTE_INLINE = PALETTE.reduce<Record<string, { dark: string[]; light: string[] }>>((acc, s) => {
  acc[s.id] = {
    dark:  [s.dark.accent,  s.dark.hover,  s.dark.bg],
    light: [s.light.accent, s.light.hover, s.light.bg],
  }
  return acc
}, {})
