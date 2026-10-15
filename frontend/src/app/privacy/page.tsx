import LegalPage, { H2, P, UL } from '@/components/LegalPage'
import { LEGAL } from '@/lib/legal'

export const metadata = { title: "Privacy Policy — MummyTKT's Bias Pointer" }

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro={`This policy explains what personal data ${LEGAL.business} collects, why, and what control you have over it. We handle your data in line with the Nigeria Data Protection Act 2023.`}
    >
      <H2>What we collect</H2>
      <UL items={[
        <><strong>Account details:</strong> your name, email address and password. Passwords are stored only in a scrambled (hashed) form that we can&apos;t read.</>,
        <><strong>Telegram:</strong> when you link Telegram, we store your Telegram chat ID so we can send you alerts. We don&apos;t read your other chats.</>,
        <><strong>Payments:</strong> plan, amount, date and the Paystack transaction reference. If you choose auto-renew, Paystack gives us a token that lets us charge your saved card for renewals. Your card number is held by Paystack, not by us.</>,
        <><strong>What you add:</strong> trading journal entries, price and entry-pattern alerts, the pairs you follow and your alert preferences.</>,
        <><strong>Usage and security:</strong> when you last signed in, and your IP address, used briefly to block password-guessing and abuse.</>,
      ]} />
      <P>
        Before-and-after pictures you attach to journal trades stay in your own browser on the device you used. They are
        not uploaded to our servers.
      </P>

      <H2>Why we use it</H2>
      <UL items={[
        'To run your account and deliver your alerts.',
        'To take payments and renewals you have agreed to, and to credit affiliates for referrals.',
        'To keep the platform secure and prevent fraud.',
        'To send service messages, such as renewal reminders and password-reset links, to your Telegram.',
      ]} />
      <P>We don&apos;t sell your data, and we don&apos;t use advertising trackers.</P>

      <H2>Who we share it with</H2>
      <P>Only the services needed to run the platform:</P>
      <UL items={[
        <><strong>Paystack</strong> — payment processing.</>,
        <><strong>Telegram</strong> — delivering alerts and messages to you.</>,
        <><strong>Fly.io</strong> — hosting our servers and database (located in the European Union).</>,
        <><strong>Vercel</strong> — hosting the website.</>,
      ]} />
      <P>
        If you join through someone&apos;s affiliate link or code, they see that a referral paid and their commission, with
        your email partly hidden (for example jo***@gmail.com). We may also share data where the law requires it.
      </P>

      <H2>How long we keep it</H2>
      <P>
        We keep your data while your account exists. When an account is closed, its details are deleted from the live
        database. Encrypted backup copies are deleted as backups are rotated out, normally within 30 days. Payment
        records may be kept longer where needed for accounting or legal reasons.
      </P>

      <H2>Browser storage</H2>
      <P>
        We use your browser&apos;s local storage to keep you signed in and to remember display choices such as theme,
        colour and time zone. You can clear it at any time by signing out or clearing your browser data.
      </P>

      <H2>Your rights</H2>
      <P>
        You can ask to see the personal data we hold about you, to correct it, or to delete your account. Email{' '}
        {LEGAL.email} from the address on your account and we&apos;ll respond within 30 days. If you&apos;re unhappy with
        how we handle your data, you can also complain to the Nigeria Data Protection Commission.
      </P>

      <H2>Security</H2>
      <P>
        Connections to the platform are encrypted, passwords are hashed, every request is checked against your current
        access, and backups are encrypted. No system is perfectly secure, so please use a strong password that you don&apos;t
        use elsewhere.
      </P>
    </LegalPage>
  )
}
