'use client'
import { useState, useEffect } from 'react'
import TradeLogPage from '@/components/TradeLogPage'
import EntryTester from '@/components/EntryTester'
import { useAuth } from '@/lib/auth'

type Tab = 'engulfing' | 'h4_key' | 'journal'
const TABS: Tab[] = ['engulfing', 'h4_key', 'journal']

// The owner also gets two entry journals, one per POI (Engulfing / Fresh Key Levels),
// each ranking its confirmation models on its own live trades; subscribers see only
// the Trading Journal.
function Tabs({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const b = (t: Tab, label: string) => (
    <button onClick={() => setTab(t)} style={{
      padding: '7px 16px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
      background: tab === t ? 'var(--accent)' : 'transparent', color: tab === t ? 'white' : 'var(--text-secondary)',
    }}>{label}</button>
  )
  return (
    <div style={{ display: 'flex', gap: 4, marginBottom: 18, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, width: 'fit-content', flexWrap: 'wrap' }}>
      {b('engulfing', 'Engulfing Journal')}
      {b('h4_key', 'Fresh Key Levels Journal')}
      {b('journal', 'Trading Journal')}
    </div>
  )
}

export default function JournalPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [tab, setTabState] = useState<Tab>('engulfing')
  useEffect(() => {
    try {
      const t = localStorage.getItem('mbp_jr_tab') as Tab | null
      if (t && TABS.includes(t)) setTabState(t)
    } catch { /* private mode */ }
  }, [])
  const setTab = (t: Tab) => {
    setTabState(t)
    try { localStorage.setItem('mbp_jr_tab', t) } catch { /* private mode */ }
  }

  const tabs = <Tabs tab={tab} setTab={setTab} />
  if (isOwner && tab === 'engulfing') return <EntryTester key="eng" book="live_engulfing" tabs={tabs} />
  if (isOwner && tab === 'h4_key') return <EntryTester key="key" book="live_h4_key" tabs={tabs} />
  return (
    <TradeLogPage
      tabs={isOwner ? tabs : undefined}
      config={{
        tradeType: 'live',
        pageTitle: 'Trading Journal',
        subtitle: 'Live trades you have taken',
        logButtonLabel: 'Log Trade',
        emptyStateText: 'Start logging your live trades to track performance and spot patterns.',
      }} />
  )
}
