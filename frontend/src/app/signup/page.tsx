'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Radio, CheckCircle2, ArrowLeft, Loader2 } from 'lucide-react'
import { API_BASE } from '@/lib/api'

const PLAN_LABELS: Record<string, { label: string; price: number; duration: string }> = {
  '30DAY':   { label: '30 Days',   price: 10, duration: '30 days' },
  '6MONTH':  { label: '6 Months',  price: 48, duration: '6 months' },
  '9MONTH':  { label: '9 Months',  price: 63, duration: '9 months' },
  '12MONTH': { label: '12 Months', price: 72, duration: '12 months' },
}

function SignupForm() {
  const params = useSearchParams()
  const planId = params.get('plan') ?? '30DAY'
  const plan = PLAN_LABELS[planId] ?? PLAN_LABELS['30DAY']

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [telegram, setTelegram] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim()) { setError('Please enter your name.'); return }
    if (!email.trim() || !email.includes('@')) { setError('Please enter a valid email.'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/public/signup-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), email: email.trim(), plan: planId, telegram: telegram.trim() }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Something went wrong. Please try again.')
      }
      setDone(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%', background: 'var(--bullish-bg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px',
        }}>
          <CheckCircle2 size={28} color="var(--bullish)" />
        </div>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 10 }}>Request received!</h2>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 340, margin: '0 auto 28px' }}>
          Your sign-up request has been sent. You&apos;ll receive your login credentials via email
          once payment is confirmed.
        </p>
        <Link href="/" style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '9px 20px', borderRadius: 9,
          background: 'var(--card)', border: '1px solid var(--border)',
          color: 'var(--text-secondary)', fontSize: 13, textDecoration: 'none',
        }}>
          <ArrowLeft size={13} /> Back to home
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Plan summary */}
      <div style={{
        background: 'var(--accent-bg)', border: '1px solid rgba(99,102,241,0.25)',
        borderRadius: 10, padding: '14px 18px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>Selected plan</p>
          <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--accent-hover)' }}>{plan.label}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>${plan.price}</p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{plan.duration}</p>
        </div>
      </div>

      {/* Fields */}
      {[
        { id: 'name',     label: 'Full name',         value: name,     set: setName,     type: 'text',  placeholder: 'Your name',         required: true },
        { id: 'email',    label: 'Email address',      value: email,    set: setEmail,    type: 'email', placeholder: 'you@example.com',   required: true },
        { id: 'telegram', label: 'Telegram username (optional)', value: telegram, set: setTelegram, type: 'text', placeholder: '@yourusername', required: false },
      ].map(({ id, label, value, set, type, placeholder, required }) => (
        <div key={id}>
          <label htmlFor={id} style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            {label}
          </label>
          <input
            id={id} type={type} value={value} placeholder={placeholder}
            onChange={e => set(e.target.value)} required={required}
            style={{
              width: '100%', padding: '10px 14px', borderRadius: 9,
              border: '1px solid var(--border)', background: 'var(--card)',
              color: 'var(--text-primary)', fontSize: 14,
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>
      ))}

      {error && (
        <p style={{ fontSize: 13, color: 'var(--bearish)', padding: '10px 14px', background: 'var(--bearish-bg)', borderRadius: 8 }}>
          {error}
        </p>
      )}

      <button type="submit" disabled={loading} style={{
        padding: '12px', borderRadius: 10, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
        background: 'var(--accent)', color: 'white', fontSize: 14, fontWeight: 700,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        opacity: loading ? 0.7 : 1, marginTop: 4,
      }}>
        {loading ? <><Loader2 size={15} className="spin" /> Sending…</> : 'Send sign-up request'}
      </button>

      <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
        Already have an account?{' '}
        <Link href="/login" style={{ color: 'var(--accent-hover)', textDecoration: 'none', fontWeight: 600 }}>Sign in</Link>
      </p>
    </form>
  )
}

export default function SignupPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 20px' }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 12px rgba(99,102,241,0.4)',
          }}>
            <Radio size={16} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.2 }}>MummyTKT&apos;s</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>Bias Pointer</div>
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '28px 28px' }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>Request access</h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.6 }}>
            Fill in your details and we&apos;ll send payment instructions. Access is set up manually once payment is confirmed.
          </p>
          <Suspense fallback={<p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</p>}>
            <SignupForm />
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
