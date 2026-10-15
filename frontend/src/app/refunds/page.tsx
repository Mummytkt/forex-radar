import Link from 'next/link'
import LegalPage, { H2, P, UL } from '@/components/LegalPage'
import { LEGAL } from '@/lib/legal'

export const metadata = { title: "Refunds & Cancellation — MummyTKT's Bias Pointer" }

export default function RefundsPage() {
  return (
    <LegalPage
      title="Refunds & Cancellation"
      intro="You can cancel at any time and keep what you paid for. Payments themselves aren't refunded, except when we've charged you by mistake."
    >
      <H2>Cancelling</H2>
      <UL items={[
        <>Turn off auto-renew any time in <strong>Account → Billing</strong>. No email or reason needed.</>,
        'You won\'t be charged again.',
        'You keep full access until the end of the period you already paid for.',
        'You can turn auto-renew back on, or buy a new plan, whenever you like.',
      ]} />

      <H2>Free trial</H2>
      <P>
        The card check at the start of a trial is refunded straight away. If you don&apos;t want to continue after the
        trial, turn off auto-renew before the 7 days end and you won&apos;t be charged.
      </P>

      <H2>Refunds</H2>
      <P>
        Because you get access to alerts and content as soon as you pay, payments for plans and renewals are{' '}
        <strong>not refundable</strong>, including when you cancel part-way through a period. We will refund in full:
      </P>
      <UL items={[
        'a duplicate charge, or a charge for the wrong amount;',
        'a renewal taken after you had already turned off auto-renew;',
        'any other payment taken because of an error on our side.',
      ]} />
      <P>
        To report a charge like this, email {LEGAL.email} within 14 days with your Paystack payment reference (it
        starts with <code>mbp_</code>). Approved refunds go back to the original payment method through Paystack and
        usually arrive within 5–10 working days.
      </P>

      <H2>Your legal rights</H2>
      <P>
        Nothing in this policy limits any rights you have under consumer protection law. See also our{' '}
        <Link href="/terms" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>Terms of Service</Link>.
      </P>
    </LegalPage>
  )
}
