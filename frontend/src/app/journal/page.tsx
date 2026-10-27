'use client'
import { useState, useEffect } from 'react'
import TradeLogPage from '@/components/TradeLogPage'
import EntryTester from '@/components/EntryTester'
import { useAuth } from '@/lib/auth'

type Tab = 'entries' | 'journal'

// The owner also gets the Entry Journal (POIs × entries, like the Backtest page's
// Entry Tester, but its own live trades); subscribers see only the Trading Journal.
function Tabs({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const b = (t: Tab, label: string) => (
    <button onClick={() => setTab(t)} style={{
      padding: '7px 16px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
      background: tab === t ? 'var(--accent)' : 'transparent', color: tab === t ? 'white' : 'var(--text-secondary)',
    }}>{label}</button>
  )
  return (
    <div style={{ display: 'flex', gap: 4, marginBottom: 18, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, width: 'fit-content' }}>
      {b('entries', 'Entry Journal')}
      {b('journal', 'Trading Journal')}
    </div>
  )
}

export default function JournalPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [tab, setTabState] = useState<Tab>('entries')
  useEffect(() => {
    try { if (localStorage.getItem('mbp_jr_tab') === 'journal') setTabState('journal') } catch { /* private mode */ }
  }, [])
  const setTab = (t: Tab) => {
    setTabState(t)
    try { localStorage.setItem('mbp_jr_tab', t) } catch { /* private mode */ }
  }

  if (isOwner && tab === 'entries') return <EntryTester book="live" tabs={<Tabs tab={tab} setTab={setTab} />} />
  return (
    <TradeLogPage
      tabs={isOwner ? <Tabs tab={tab} setTab={setTab} /> : undefined}
      config={{
        tradeType: 'live',
        pageTitle: 'Trading Journal',
        subtitle: 'Live trades you have taken',
        logButtonLabel: 'Log Trade',
        emptyStateText: 'Start logging your live trades to track performance and spot patterns.',
      }} />
  )
}
