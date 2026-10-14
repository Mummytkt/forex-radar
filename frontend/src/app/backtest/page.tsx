import TradeLogPage from '@/components/TradeLogPage'

export default function BacktestPage() {
  return (
    <TradeLogPage config={{
      tradeType: 'backtest',
      pageTitle: 'Backtest Journal',
      subtitle: 'Trades backtested against historical data',
      logButtonLabel: 'Log Backtest',
      emptyStateText: 'Log your backtested trades here to review your strategy against past market conditions.',
    }} />
  )
}
