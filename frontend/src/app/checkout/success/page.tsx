'use client'
import { useState, useEffect, Suspense, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Radio, CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { API_BASE } from '@/lib/api'

function SuccessInner() {
  const params = useSearchParams()
  const router = useRouter()
  const reference = params.get('reference') ?? ''

  const [state, setState] = useState<'checking' | 'paid' | 'setpw' | 'pending' | 'error'>('checking')
  const [email, setEmail] = useState('')
  const [planLabel, setPlanLabel] = useState('')
  const [pwToken, setPwToken] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const verify = useCallback(async () => {
    if (!reference) { setState('error'); return }
    try {
      const r = await fetch(`${API_BASE}/api/public/checkout/verify?reference=${encodeURIComponent(reference)}`)
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || 'verify failed')
      setEmail(d.email || '')
      setPlanLabel(d.plan || '')
      if (d.status === 'paid') {
        if (d.set_password_token) { setPwToken(d.set_password_token); setState('setpw') }
        else setState('paid')
      } else {
        setState('pending')
      }
    } catch {
      setState('error')
    }
  }, [reference])

  useEffect(() => { verify() }, [verify])

  // While pending (webhook not in yet), re-check a few times
  useEffect(() => {
    if (state !== 'pending') return
    const id = setTimeout(verify, 4000)
    return () => clearTimeout(id)
  }, [state, verify])

  const setPw = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return }
    setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/api/public/set-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: pwToken, password }),
      })
      const d = await r.json()
      if (!r.ok || !d.token) throw new Error(d.detail || 'Could not set password.')
      localStorage.setItem('mbp_token', d.token)
      router.replace('/dashboard')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setBusy(false)
    }
  }

  const ring = (icon: React.ReactNode, bg: string) => (
    <div style={{ width: 56, height: 56, borderRadius: '50%', background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>{icon}</div>
  )

  if (state === 'checking' || state === 'pending') {
    return (
      <div style={{ textAlign: 'center', padding: '30px 0' }}>
        {ring(<Loader2 size={26} className="spin" color="var(--accent-hover)" />, 'var(--accent-bg)')}
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Confirming your payment…</h2>
        <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 340, margin: '0 auto' }}>
          This usually takes a few seconds. You can keep this page open.
        </p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div style={{ textAlign: 'center', padding: '30px 0' }}>
        {ring(<XCircle size={26} color="var(--bearish)" />, 'var(--bearish-bg)')}
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>We couldn&apos;t confirm this payment</h2>
        <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 360, margin: '0 auto 24px' }}>
          If you were charged, your access is being set up — check your email, or contact support with your reference.
        </p>
        <Link href="/" style={{ fontSize: 13, color: 'var(--accent-hover)', textDecoration: 'none' }}>Back to home</Link>
      </div>
    )
  }

  if (state === 'setpw') {
    return (
      <div>
        {ring(<CheckCircle2 size={26} color="var(--bullish)" />, 'var(--bullish-bg)')}
        <h2 style={{ fontSize: 21, fontWeight: 700, textAlign: 'center', marginBottom: 6 }}>Payment confirmed 🎉</h2>
        <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', textAlign: 'center', lineHeight: 1.7, marginBottom: 22 }}>
          {planLabel} activated for <strong>{email}</strong>. Set a password to finish and log in.
        </p>
        <form onSubmit={setPw} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Choose a password (min 8 characters)"
            style={{ width: '100%', padding: '11px 14px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-primary)', fontSize: 14, outline: 'none', boxSizing: 'border-box' }} />
          {error && <p style={{ fontSize: 13, color: 'var(--bearish)' }}>{error}</p>}
          <button type="submit" disabled={busy} style={{ padding: '12px', borderRadius: 10, border: 'none', cursor: busy ? 'not-allowed' : 'pointer', background: 'var(--accent)', color: 'white', fontSize: 14, fontWeight: 700, opacity: busy ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            {busy ? <><Loader2 size={15} className="spin" /> Finishing…</> : 'Set password & enter dashboard'}
          </button>
        </form>
      </div>
    )
  }

  // paid, existing account
  return (
    <div style={{ textAlign: 'center', padding: '20px 0' }}>
      {ring(<CheckCircle2 size={26} color="var(--bullish)" />, 'var(--bullish-bg)')}
      <h2 style={{ fontSize: 21, fontWeight: 700, marginBottom: 8 }}>Payment confirmed 🎉</h2>
      <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 360, margin: '0 auto 24px' }}>
        {planLabel} is active on <strong>{email}</strong>. Sign in to access your dashboard.
      </p>
      <Link href="/login" style={{ display: 'inline-block', padding: '11px 24px', borderRadius: 10, background: 'var(--accent)', color: 'white', fontSize: 14, fontWeight: 700, textDecoration: 'none' }}>Sign in</Link>
    </div>
  )
}

export default function CheckoutSuccessPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 20px' }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24, justifyContent: 'center' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Radio size={16} color="white" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>MummyTKT&apos;s Bias Pointer</div>
        </div>
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '30px 28px' }}>
          <Suspense fallback={<p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center' }}>Loading…</p>}>
            <SuccessInner />
          </Suspense>
        </div>
      </div>
    </div>
  )
}
