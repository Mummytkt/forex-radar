'use client'
import { useState, useEffect } from 'react'
import { EyeOff, Eye } from 'lucide-react'

export type JournalTab = 'engulfing' | 'h4_key' | 'journal'
const TABS: JournalTab[] = ['engulfing', 'h4_key', 'journal']
const HIDE_KEY = 'mbp_hide_engulfing'   // one choice for the Journal and Backtest pages

// The owner's journal tabs (Engulfing / Fresh Key Levels / the trade journal), the
// chosen tab remembered under tabKey. The Engulfing Journal can be hidden and shown
// again; its trades stay saved while it's hidden.
export function useJournalTabs(tabKey: string, journalLabel: string): [JournalTab, React.ReactNode] {
  const [tab, setTabState] = useState<JournalTab>('engulfing')
  const [hideEng, setHideEng] = useState(false)
  useEffect(() => {
    try {
      const h = localStorage.getItem(HIDE_KEY) === '1'
      setHideEng(h)
      const t = localStorage.getItem(tabKey) as JournalTab | null
      if (t && TABS.includes(t)) setTabState(h && t === 'engulfing' ? 'h4_key' : t)
      else if (h) setTabState('h4_key')
    } catch { /* private mode */ }
  }, [tabKey])
  const setTab = (t: JournalTab) => {
    setTabState(t)
    try { localStorage.setItem(tabKey, t) } catch { /* private mode */ }
  }
  const toggleEng = (hide: boolean) => {
    setHideEng(hide)
    try { localStorage.setItem(HIDE_KEY, hide ? '1' : '0') } catch { /* private mode */ }
    if (hide && tab === 'engulfing') setTab('h4_key')
    if (!hide) setTab('engulfing')
  }

  const b = (t: JournalTab, label: string) => (
    <button onClick={() => setTab(t)} style={{
      padding: '7px 16px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
      background: tab === t ? 'var(--accent)' : 'transparent', color: tab === t ? 'white' : 'var(--text-secondary)',
    }}>{label}</button>
  )
  const small: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 5, border: 'none', background: 'none', cursor: 'pointer',
    fontSize: 11.5, fontWeight: 600, color: 'var(--text-muted)', padding: '4px 6px',
  }
  const node = (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 18 }}>
      <div style={{ display: 'flex', gap: 4, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, width: 'fit-content', flexWrap: 'wrap' }}>
        {!hideEng && b('engulfing', 'Engulfing Journal')}
        {b('h4_key', 'Fresh Key Levels Journal')}
        {b('journal', journalLabel)}
      </div>
      {hideEng
        ? <button onClick={() => toggleEng(false)} style={small} title="Bring the Engulfing Journal back (its trades are still saved)"><Eye size={13} /> Show Engulfing Journal</button>
        : <button onClick={() => toggleEng(true)} style={small} title="Hide the Engulfing Journal tab. Its trades stay saved; show it again any time."><EyeOff size={13} /> Hide Engulfing</button>}
    </div>
  )
  return [tab, node]
}
