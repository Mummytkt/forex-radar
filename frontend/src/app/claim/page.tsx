'use client'
import { useState } from 'react'
import Link from 'next/link'
import { CheckCircle2 } from 'lucide-react'
import AuthCard, { inputStyle, labelStyle, buttonStyle, linkStyle } from '@/components/AuthCard'
import { API_BASE } from '@/lib/api'

const errBox: React.CSSProperties = { padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }

export default function ClaimPage() {
  const [email, setEmail] = useState('')
  const [reference, setReference] = useState('')
  const [setToken, setSetToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const findPayment = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/api/public/claim-account`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, reference }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail || 'Something went wrong. Please try again.')
      setSetToken(d.set_password_token)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError(''); setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/api/public/set-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: setToken, password }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail || 'Could not set your password.')
      try { localStorage.setItem('mbp_token', d.token) } catch {}
      setDone(true)
      setTimeout(() => { window.location.href = '/hub' }, 1200)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not set your password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard
      title="Finish setting up your account"
      subtitle="Paid but closed the page before choosing a password? Confirm your payment and set one now."
      footer={<Link href="/login" style={linkStyle}>Back to sign in</Link>}
    >
      {done ? (
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <CheckCircle2 size={40} color="var(--bullish)" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontWeight: 700, color: 'var(--text-primary)' }}>You&apos;re all set</p>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6 }}>Taking you to your dashboard…</p>
        </div>
      ) : !setToken ? (
        <form onSubmit={findPayment} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label htmlFor="claim-email" style={labelStyle}>Email you paid with</label>
            <input id="claim-email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" autoComplete="email" style={inputStyle} />
          </div>
          <div>
            <label htmlFor="claim-ref" style={labelStyle}>Payment reference</label>
            <input id="claim-ref" required value={reference} onChange={e => setReference(e.target.value)}
              placeholder="e.g. mbp_3f9c1a…" style={{ ...inputStyle, fontFamily: 'monospace' }} />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.6 }}>
              Find it in the receipt email Paystack sent you. It starts with <code>mbp_</code>.
            </p>
          </div>
          {error && <div style={errBox}>{error}</div>}
          <button type="submit" disabled={busy || !email || !reference} style={buttonStyle(busy || !email || !reference)}>
            {busy ? 'Checking…' : 'Find my payment'}
          </button>
        </form>
      ) : (
        <form onSubmit={savePassword} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ fontSize: 13, color: 'var(--bullish)', fontWeight: 600 }}>Payment found. Choose your password.</p>
          <div>
            <label htmlFor="claim-password" style={labelStyle}>Password</label>
            <input id="claim-password" type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="Min. 8 characters" autoComplete="new-password" style={inputStyle} />
          </div>
          <div>
            <label htmlFor="claim-confirm" style={labelStyle}>Confirm password</label>
            <input id="claim-confirm" type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
              placeholder="Repeat password" autoComplete="new-password" style={inputStyle} />
          </div>
          {error && <div style={errBox}>{error}</div>}
          <button type="submit" disabled={busy || !password || !confirm} style={buttonStyle(busy || !password || !confirm)}>
            {busy ? 'Saving…' : 'Set password & sign in'}
          </button>
        </form>
      )}
    </AuthCard>
  )
}
