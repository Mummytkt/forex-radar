import LegalPage, { H2, P, UL } from '@/components/LegalPage'
import { LEGAL } from '@/lib/legal'

export const metadata = { title: "Risk Disclaimer — MummyTKT's Bias Pointer" }

export default function RiskPage() {
  return (
    <LegalPage
      title="Risk Disclaimer"
      intro="Trading forex, metals, indices and cryptocurrencies carries a high risk of losing money. Please read this before acting on any alert."
    >
      <H2>Not financial advice</H2>
      <P>
        {LEGAL.business} provides market analysis for education and information. Alerts tell you when our rules see a
        confirmed directional bias. They are not a recommendation to buy or sell, they don&apos;t take your circumstances
        into account, and we are not a licensed financial or investment adviser.
      </P>

      <H2>Alerts are a bias, not an entry</H2>
      <P>
        An alert says which direction the Daily and H4 structure favours. It does not give an entry price, stop loss or
        take profit. Where and whether to enter, how much to risk, and when to exit are your decisions.
      </P>

      <H2>The risks</H2>
      <UL items={[
        'Leveraged products such as forex and CFDs can lose you more than you deposit.',
        'Prices can move fast, gap over weekends and news, and slip past your orders.',
        'A confirmed bias can be wrong, and a series of losses is normal in any strategy.',
        'Market data may be delayed or differ slightly between data providers and brokers.',
        'Past results, including any track record shown on this site, do not guarantee future results.',
      ]} />

      <H2>Trade responsibly</H2>
      <P>
        Only trade with money you can afford to lose, use risk management on every trade, and get independent advice if
        you&apos;re unsure. You are fully responsible for your trading decisions and their results.
      </P>
    </LegalPage>
  )
}
