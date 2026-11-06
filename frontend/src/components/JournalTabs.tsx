'use client'
import { useState, useEffect } from 'react'
import { EyeOff, Eye } from 'lucide-react'

export type JournalTab = 'scl' | 'hl_liq' | 'engulfing' | 'h4_key' | 'journal'
const TABS: JournalTab[] = ['scl', 'hl_liq', 'engulfing', 'h4_key', 'journal']
const OLD: JournalTab[] = ['engulfing', 'h4_key']
const OLD_KEY = 'mbp_show_old_journals'   // one choice for the Journal and Backtest pages

// The owner's journal tabs (one per entry model, then the trade journal), the chosen
// tab remembered under tabKey. The older Engulfing / Fresh Key Levels journals are
// hidden until asked for; their trades stay saved.
export function useJournalTabs(tabKey: string, journalLabel: string): [JournalTab, React.ReactNode] {
  const [tab, setTabState] = useState<JournalTab>('scl')
  const [showOld, setShowOld] = useState(false)
  useEffect(() => {
    try {
      const o = localStorage.getItem(OLD_KEY) === '1'
      setShowOld(o)
      const t = localStorage.getItem(tabKey) as JournalTab | null
      if (t && TABS.includes(t) && (o || !OLD.includes(t))) setTabState(t)
    } catch { /* private mode */ }
  }, [tabKey])
  const setTab = (t: JournalTab) => {
    setTabState(t)
    try { localStorage.setItem(tabKey, t) } catch { /* private mode */ }
  }
  const toggleOld = (show: boolean) => {
    setShowOld(show)
    try { localStorage.setItem(OLD_KEY, show ? '1' : '0') } catch { /* private mode */ }
    if (!show && OLD.includes(tab)) setTab('scl')
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
        {b('scl', 'H1 entry')}
        {b('hl_liq', 'M15 entry')}
        {showOld && b('engulfing', 'Engulfing Journal')}
        {showOld && b('h4_key', 'Fresh Key Levels Journal')}
        {b('journal', journalLabel)}
      </div>
      {showOld
        ? <button onClick={() => toggleOld(false)} style={small} title="Hide the older journals (their trades stay saved)"><EyeOff size={13} /> Hide old journals</button>
        : <button onClick={() => toggleOld(true)} style={small} title="Show the Engulfing and Fresh Key Levels journals with their saved trades"><Eye size={13} /> Show old journals</button>}
    </div>
  )
  return [tab, node]
}
