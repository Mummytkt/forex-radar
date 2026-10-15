'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Radio, ArrowLeft, Loader2, Repeat, CreditCard, Gift } from 'lucide-react'
import { API_BASE } from '@/lib/api'

const PLANS: Record<string, { label: string; price: number; duration: string; color: string; trial?: boolean }> = {
  'TRIAL':   { label: '7-Day Free Trial', price: 10, duration: 'free for 7 days, then $10/mo', color: '#ec4899', trial: true },
  '30DAY':   { label: '30 Days',   price: 10, duration: '30 days', color: '#3b82f6' },
  '6MONTH':  { label: '6 Months',  price: 48, duration: '6 months', color: '#10b981' },
  '9MONTH':  { label: '9 Months',  price: 63, duration: '9 months', color: '#7c3aed' },
  '12MONTH': { label: '12 Months', price: 72, duration: '12 months', color: '#f59e0b' },
}

function CheckoutForm() {
  const params = useSearchParams()
  const planId = (params.get('plan') ?? '30DAY').toUpperCase()
  const plan = PLANS[planId] ?? PLANS['30DAY']
  const isTrial = !!plan.trial

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [billing, setBilling] = useState<'once' | 'auto'>('once')
  const [referral, setReferral] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const ref = params.get('ref')
    if (ref) setReferral(ref.toUpperCase())
  }, [params])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim()) { setError('Please enter your name.'); return }
    if (!email.trim() || !email.includes('@')) { setError('Please enter a valid email.'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/public/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan: planId, name: name.trim(), email: email.trim(),
          billing: isTrial ? 'auto' : billing,
          referral_code: referral.trim() || null,
        }),
      })
      const d = await res.json().catch(() => ({}))
      if (!res.ok || !d.authorization_url) throw new Error(d.detail || 'Could not start checkout. Please try again.')
      window.location.href = d.authorization_url
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setLoading(false)
    }
  }

  const input: React.CSSProperties = {
    width: '100%', padding: '11px 14px', borderRadius: 10, border: '1px solid var(--border)',
    background: 'var(--bg)', color: 'var(--text-primary)', fontSize: 14, outline: 'none', boxSizing: 'border-box',
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Plan summary */}
      <div style={{
        background: `${plan.color}1f`, border: `1px solid ${plan.color}55`, borderRadius: 12,
        padding: '16px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        boxShadow: `0 14px 36px -22px ${plan.color}`,
      }}>
        <div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>{isTrial ? 'Starting' : 'Selected plan'}</p>
          <p style={{ fontSize: 16, fontWeight: 800, color: plan.color }}>{plan.label}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: 24, fontWeight: 800, color: plan.color }}>{isTrial ? '$0' : `$${plan.price}`}</p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{isTrial ? 'today' : plan.duration}</p>
        </div>
      </div>

      {isTrial && (
        <div style={{ display: 'flex', gap: 9, alignItems: 'flex-start', fontSize: 12.5, color: 'var(--text-secondary)', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '11px 13px', lineHeight: 1.6 }}>
          <Gift size={15} color={plan.color} style={{ flexShrink: 0, marginTop: 1 }} />
          <span><strong>7 days free.</strong> We securely save your card now (and refund the verification). After 7 days you&apos;re charged <strong>${plan.price}</strong> and it renews monthly — cancel anytime.</span>
        </div>
      )}

      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Full name</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" style={input} />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Email address</label>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={input} />
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>Your login + alerts are tied to this email.</p>
      </div>

      {/* Billing choice — hidden for trial (always recurring) */}
      {!isTrial && (
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Billing</label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {([['once', 'Pay once', CreditCard, 'Access expires, no renewal'], ['auto', 'Renews automatically', Repeat, 'Cancel anytime']] as const).map(([val, lbl, Icon, note]) => (
              <button key={val} type="button" onClick={() => setBilling(val as 'once' | 'auto')} style={{
                textAlign: 'left', padding: '12px 14px', borderRadius: 11, cursor: 'pointer',
                border: `1px solid ${billing === val ? plan.color : 'var(--border)'}`,
                background: billing === val ? `${plan.color}1a` : 'var(--bg)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, fontWeight: 700, color: billing === val ? plan.color : 'var(--text-primary)' }}>
                  <Icon size={14} /> {lbl}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{note}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Referral code <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
        </label>
        <input value={referral} onChange={e => setReferral(e.target.value.toUpperCase())} placeholder="MBPXXXXXX" style={input} />
      </div>

      {error && <p style={{ fontSize: 13, color: 'var(--bearish)', padding: '10px 14px', background: 'var(--bearish-bg)', borderRadius: 8 }}>{error}</p>}

      <button type="submit" disabled={loading} style={{
        padding: '13px', borderRadius: 11, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
        background: plan.color, color: 'white', fontSize: 14.5, fontWeight: 800,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, opacity: loading ? 0.7 : 1, marginTop: 4,
      }}>
        {loading ? <><Loader2 size={15} className="spin" /> Redirecting to secure checkout…</> : (isTrial ? 'Start my free trial' : 'Continue to payment')}
      </button>

      <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
        Prices in USD. You&apos;ll be charged the equivalent in NGN (shown on the Paystack checkout).
        Payments processed securely by Paystack — card details never touch our servers.
      </p>
      <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
        Already have an account? <Link href="/login" style={{ color: 'var(--accent-hover)', textDecoration: 'none', fontWeight: 600 }}>Sign in</Link>
      </p>
    </form>
  )
}

export default function CheckoutPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 20px' }}>
      <div style={{ width: '100%', maxWidth: 440 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 12px rgba(99,102,241,0.4)' }}>
            <Radio size={16} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.2 }}>MummyTKT&apos;s</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>Bias Pointer</div>
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '28px' }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4, letterSpacing: '-0.01em' }}>Secure <span className="lp-grad1">checkout</span></h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.6 }}>
            Fill in your details and continue to payment. Access is set up automatically the moment your payment confirms.
          </p>
          <Suspense fallback={<p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>}>
            <CheckoutForm />
          </Suspense>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Link href="/" style={{ fontSize: 12, color: 'var(--text-muted)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <ArrowLeft size={12} /> Back to home
          </Link>
        </div>
      </div>
    </div>
  )
}
