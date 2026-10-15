'use client'
import { useState, useEffect } from 'react'
import { Radio, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const { login, user, loading, authEnabled } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const router = useRouter()

  useEffect(() => {
    if (!loading && user) router.replace('/dashboard')
    if (!loading && !authEnabled) router.replace('/dashboard')
  }, [loading, user, authEnabled, router])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 13, background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 14px',
            boxShadow: '0 0 24px rgba(99,102,241,0.4)',
          }}>
            <Radio size={22} color="white" />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
            MummyTKT's
          </h1>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--accent)', marginTop: 2 }}>
            Bias Pointer
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
            Sign in to access your dashboard
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: 14, padding: 28, boxShadow: 'var(--shadow)',
        }}>
          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Email address
              </label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com" autoComplete="email"
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 14,
                  background: 'var(--bg)', border: '1px solid var(--border)',
                  color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Your password" autoComplete="current-password"
                  style={{
                    width: '100%', padding: '10px 40px 10px 12px', borderRadius: 8, fontSize: 14,
                    background: 'var(--bg)', border: '1px solid var(--border)',
                    color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
                  }}
                />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0,
                  }}>
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting || !email || !password}
              style={{
                padding: '11px', borderRadius: 9, fontSize: 14, fontWeight: 700,
                background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer',
                opacity: submitting || !email || !password ? 0.6 : 1,
                boxShadow: '0 2px 10px rgba(99,102,241,0.35)',
                transition: 'opacity 0.1s',
                marginTop: 4,
              }}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 20, lineHeight: 1.9 }}>
          <a href="/forgot" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>Forgot password?</a>
          <br />
          Paid but never set a password?{' '}
          <a href="/claim" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>Finish setting up</a>
        </p>
      </div>
    </div>
  )
}
