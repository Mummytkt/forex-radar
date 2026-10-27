'use client'
import { useState, useEffect } from 'react'
import TradeLogPage from '@/components/TradeLogPage'
import EntryTester from '@/components/EntryTester'
import { useAuth } from '@/lib/auth'

type Tab = 'engulfing' | 'h4_key' | 'journal'
const TABS: Tab[] = ['engulfing', 'h4_key', 'journal']

// The owner also gets two backtest entry journals, one per POI (Engulfing / Fresh
// Key Levels), like the Trading Journal page; subscribers see only the Backtest Journal.
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
      {b('journal', 'Backtest Journal')}
    </div>
  )
}

export default function BacktestPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [tab, setTabState] = useState<Tab>('engulfing')
  useEffect(() => {
    try {
      const t = localStorage.getItem('mbp_bt_tab2') as Tab | null
      if (t && TABS.includes(t)) setTabState(t)
    } catch { /* private mode */ }
  }, [])
  const setTab = (t: Tab) => {
    setTabState(t)
    try { localStorage.setItem('mbp_bt_tab2', t) } catch { /* private mode */ }
  }

  const tabs = <Tabs tab={tab} setTab={setTab} />
  if (isOwner && tab === 'engulfing') return <EntryTester key="bt-eng" book="bt_engulfing" tabs={tabs} />
  if (isOwner && tab === 'h4_key') return <EntryTester key="bt-key" book="bt_h4_key" tabs={tabs} />
  return (
    <TradeLogPage
      tabs={isOwner ? tabs : undefined}
      config={{
        tradeType: 'backtest',
        pageTitle: 'Backtest Journal',
        subtitle: 'Trades backtested against historical data',
        logButtonLabel: 'Log Backtest',
        emptyStateText: 'Log your backtested trades here to review your strategy against past market conditions.',
      }} />
  )
}
