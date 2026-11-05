'use client'
import TradeLogPage from '@/components/TradeLogPage'
import EntryTester from '@/components/EntryTester'
import { useAuth } from '@/lib/auth'
import { useJournalTabs } from '@/components/JournalTabs'

// The owner also gets an entry journal per entry model (SCL / high-low liquidity before
// the POI; older ones on request), each ranking its confirmations on its own live trades;
// subscribers see only the Trading Journal.
export default function JournalPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [tab, tabs] = useJournalTabs('mbp_jr_tab', 'Trading Journal')
  if (isOwner && tab === 'scl') return <EntryTester key="scl" book="live_scl" tabs={tabs} />
  if (isOwner && tab === 'hl_liq') return <EntryTester key="hl" book="live_hl_liq" tabs={tabs} />
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
