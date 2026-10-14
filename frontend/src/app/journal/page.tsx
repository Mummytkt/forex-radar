import TradeLogPage from '@/components/TradeLogPage'

export default function JournalPage() {
  return (
    <TradeLogPage config={{
      tradeType: 'live',
      pageTitle: 'Trading Journal',
      subtitle: 'Live trades you have taken',
      logButtonLabel: 'Log Trade',
      emptyStateText: 'Start logging your live trades to track performance and spot patterns.',
    }} />
  )
}
