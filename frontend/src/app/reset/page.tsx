'use client'
import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { CheckCircle2 } from 'lucide-react'
import AuthCard, { inputStyle, labelStyle, buttonStyle, linkStyle } from '@/components/AuthCard'
import { API_BASE } from '@/lib/api'

function ResetForm() {
  const token = useSearchParams().get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  if (!token) {
    return (
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
        This page needs the link from your reset message. <Link href="/forgot" style={linkStyle}>Request a new link</Link>.
      </p>
    )
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError(''); setSaving(true)
    try {
      const r = await fetch(`${API_BASE}/api/auth/reset`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail || 'Could not reset your password.')
      try { localStorage.setItem('mbp_token', d.token) } catch {}
      setDone(true)
      setTimeout(() => { window.location.href = '/hub' }, 1200)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not reset your password.')
    } finally {
      setSaving(false)
    }
  }

  if (done) {
    return (
      <div style={{ textAlign: 'center', padding: '8px 0' }}>
        <CheckCircle2 size={40} color="var(--bullish)" style={{ margin: '0 auto 12px' }} />
        <p style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Password updated</p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6 }}>Taking you to your dashboard…</p>
      </div>
    )
  }

  const disabled = saving || !password || !confirm
  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <label htmlFor="reset-password" style={labelStyle}>New password</label>
        <input id="reset-password" type="password" value={password} onChange={e => setPassword(e.target.value)}
          placeholder="Min. 8 characters" autoComplete="new-password" style={inputStyle} />
      </div>
      <div>
        <label htmlFor="reset-confirm" style={labelStyle}>Confirm new password</label>
        <input id="reset-confirm" type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
          placeholder="Repeat password" autoComplete="new-password" style={inputStyle} />
      </div>
      {error && (
        <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>
          {error} {error.includes('expired') || error.includes('invalid') ? <Link href="/forgot" style={linkStyle}>Get a new link</Link> : null}
        </div>
      )}
      <button type="submit" disabled={disabled} style={buttonStyle(disabled)}>
        {saving ? 'Saving…' : 'Set new password & sign in'}
      </button>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
        For your security, this signs you out on every other device.
      </p>
    </form>
  )
}

export default function ResetPage() {
  return (
    <AuthCard title="Choose a new password" footer={<Link href="/login" style={linkStyle}>Back to sign in</Link>}>
      <Suspense fallback={<p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</p>}>
        <ResetForm />
      </Suspense>
    </AuthCard>
  )
}
