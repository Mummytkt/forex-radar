import Link from 'next/link'
import LegalPage, { H2, P, UL } from '@/components/LegalPage'
import { LEGAL } from '@/lib/legal'

export const metadata = { title: "Terms of Service — MummyTKT's Bias Pointer" }

const a = { color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 } as const

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      intro={`These terms are the agreement between you and ${LEGAL.business} ("we", "us"). By creating an account, starting a trial or paying for a plan, you agree to them. If you don't agree, please don't use the service.`}
    >
      <H2>1. What the service is</H2>
      <P>
        {LEGAL.business} analyses the forex, metals, indices and crypto markets using a fixed set of price-action rules
        and tells you when a directional bias (buy or sell) has been confirmed on the Daily and H4 timeframes. Alerts are
        delivered to your linked Telegram and shown on your dashboard. The platform also includes a trading journal,
        price and entry-pattern alerts, and tutorial videos.
      </P>
      <P>
        Alerts describe market direction. They are <strong>not</strong> entry or exit instructions, and they are not
        personal financial advice. Read the <Link href="/risk" style={a}>Risk Disclaimer</Link> before you trade.
      </P>

      <H2>2. Who can use it</H2>
      <UL items={[
        'You must be at least 18 years old and able to enter a binding agreement.',
        'Each account is for one person. Don\'t share your login or forward alerts to people who haven\'t subscribed.',
        'Keep your password safe. You are responsible for activity on your account.',
      ]} />

      <H2>3. Plans and payment</H2>
      <UL items={[
        'Plans: 30 days ($10), 6 months ($48), 9 months ($63) and 12 months ($72). The price shown at checkout is the price you pay.',
        'Prices are set in US dollars. Where you pay in naira, the amount is converted at the exchange rate on the day of payment.',
        'Payments are processed by Paystack. We never see or store your full card number.',
        'You can pay once, or choose auto-renew: your saved card is charged the same plan price at the end of each period until you turn auto-renew off.',
      ]} />

      <H2>4. Free trial</H2>
      <UL items={[
        'New members can try the platform free for 7 days. The trial is limited to one per person and email address.',
        'To start a trial we verify your card with a charge that is refunded straight away.',
        'Unless you turn off auto-renew before the 7 days end, your card is charged $10 for 30 days and then every 30 days after that.',
      ]} />

      <H2>5. Cancelling</H2>
      <P>
        You can turn off auto-renew at any time in <strong>Account → Billing</strong>. You won&apos;t be charged again and
        you keep access until the end of the period you already paid for. Refunds are covered in the{' '}
        <Link href="/refunds" style={a}>Refunds &amp; Cancellation</Link> policy.
      </P>

      <H2>6. Acceptable use</H2>
      <P>You agree not to:</P>
      <UL items={[
        'resell, publish, or redistribute alerts, tutorials or strategy content;',
        'copy, scrape or automate access to the platform;',
        'try to access other people\'s accounts or data, or interfere with the service;',
        'use the affiliate programme to refer yourself or to earn commission on fake or fraudulent sign-ups.',
      ]} />

      <H2>7. Affiliate programme</H2>
      <P>
        Members can earn commission on payments from people they refer: 10% on payments from their first 10 paying
        customers and 15% after that, for as long as each customer keeps paying. Commission becomes payable 7 days after
        the customer&apos;s payment and is paid out by us manually. We may withhold commission on self-referrals, refunded
        or fraudulent payments, or where these terms are broken.
      </P>

      <H2>8. Availability</H2>
      <P>
        Alerts depend on third-party services, including TradingView market data, Telegram and our hosting providers.
        We work to keep the service running, but we can&apos;t guarantee that every alert is generated or delivered, or
        delivered at a particular time. Market data can occasionally be delayed or differ slightly from your broker.
      </P>

      <H2>9. Our content</H2>
      <P>
        The strategy material, tutorials, alert text and software belong to us. Your subscription gives you a personal,
        non-transferable right to use them while your plan is active.
      </P>

      <H2>10. Suspension and termination</H2>
      <P>
        We may suspend or close an account that breaks these terms, for example by sharing logins or redistributing
        alerts. Access also ends when a plan expires without renewal.
      </P>

      <H2>11. Liability</H2>
      <P>
        Trading decisions are yours alone. To the fullest extent the law allows, we are not liable for any trading
        losses or for indirect or consequential losses arising from your use of the service. Where liability cannot
        be excluded, our total liability is limited to the amount you paid us in the 3 months before the claim.
      </P>

      <H2>12. Changes</H2>
      <P>
        We may update these terms. When we make a material change we&apos;ll update the date above and, where it affects
        your subscription, tell you in advance on the dashboard or by Telegram. Continuing to use the service after a
        change means you accept it.
      </P>

      <H2>13. Governing law</H2>
      <P>These terms are governed by the laws of the Federal Republic of Nigeria.</P>
    </LegalPage>
  )
}
