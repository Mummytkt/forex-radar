'use client'
import TradeLogPage from '@/components/TradeLogPage'
import EntryTester from '@/components/EntryTester'
import { useAuth } from '@/lib/auth'
import { useJournalTabs } from '@/components/JournalTabs'

// The owner also gets two backtest entry journals, one per POI (Engulfing / Fresh
// Key Levels), like the Trading Journal page; subscribers see only the Backtest Journal.
export default function BacktestPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [tab, tabs] = useJournalTabs('mbp_bt_tab2', 'Backtest Journal')
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
