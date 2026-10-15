'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Send } from 'lucide-react'
import AuthCard, { inputStyle, labelStyle, buttonStyle, linkStyle } from '@/components/AuthCard'
import { API_BASE } from '@/lib/api'

export default function ForgotPage() {
  const [email, setEmail] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState('')
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setSending(true)
    try {
      const r = await fetch(`${API_BASE}/api/auth/forgot`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.detail || 'Something went wrong. Please try again.')
      setSent(d.message)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSending(false)
    }
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="We'll send a one-time reset link to the Telegram linked to your account."
      footer={<>
        <Link href="/login" style={linkStyle}>Back to sign in</Link><br />
        Paid but never set a password? <Link href="/claim" style={linkStyle}>Set it up here</Link>
      </>}
    >
      {sent ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', color: 'var(--text-primary)' }}>
            <Send size={16} color="var(--bullish)" style={{ flexShrink: 0, marginTop: 3 }} />
            <span>{sent}</span>
          </div>
          <p>Open Telegram and tap the link from the Bias Pointer bot. It works once, for 30 minutes.</p>
          <p>No Telegram linked to your account? Ask the platform owner to send you a reset link.</p>
        </div>
      ) : (
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label htmlFor="forgot-email" style={labelStyle}>Email</label>
            <input id="forgot-email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" autoComplete="email" style={inputStyle} />
          </div>
          {error && <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>{error}</div>}
          <button type="submit" disabled={sending || !email} style={buttonStyle(sending || !email)}>
            {sending ? 'Sending…' : 'Send reset link'}
          </button>
        </form>
      )}
    </AuthCard>
  )
}
