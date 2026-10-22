'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Radio, Eye, EyeOff, CheckCircle2 } from 'lucide-react'
import { API_BASE } from '@/lib/api'

function JoinForm() {
  const params = useSearchParams()
  const router = useRouter()
  const token = params.get('token') ?? ''

  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!token) router.replace('/login')
  }, [token, router])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError('')
    setSubmitting(true)
    try {
      const r = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, name, password }),
      })
      if (!r.ok) {
        const err = await r.json()
        throw new Error(err.detail || 'Registration failed')
      }
      const { token: jwt } = await r.json()
      localStorage.setItem('mbp_token', jwt)
      setDone(true)
      setTimeout(() => router.replace('/'), 1500)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <CheckCircle2 size={48} color="var(--bullish)" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>Welcome aboard!</h2>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>Redirecting to your dashboard…</p>
      </div>
    )
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Your name
        </label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Toyosi Adebowale"
          style={{ width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 14, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
        />
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Set a password
        </label>
        <div style={{ position: 'relative' }}>
          <input type={showPw ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
            placeholder="Min. 8 characters"
            style={{ width: '100%', padding: '10px 40px 10px 12px', borderRadius: 8, fontSize: 14, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
          />
          <button type="button" onClick={() => setShowPw(v => !v)}
            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}>
            {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
          Confirm password
        </label>
        <div style={{ position: 'relative' }}>
          <input type={showPw ? 'text' : 'password'} value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Repeat password"
            style={{ width: '100%', padding: '10px 40px 10px 12px', borderRadius: 8, fontSize: 14, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
          />
          <button type="button" onClick={() => setShowPw(v => !v)} aria-label={showPw ? 'Hide passwords' : 'Show passwords'}
            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}>
            {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>
      {error && (
        <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>
          {error}
          {/already been used|invalid or expired/i.test(error) && (
            <> Already set up your account? <a href="/login" style={{ color: 'var(--accent)', fontWeight: 600 }}>Log in here</a>.</>
          )}
        </div>
      )}
      <button type="submit" disabled={submitting || !name || !password || !confirm}
        style={{ padding: '11px', borderRadius: 9, fontSize: 14, fontWeight: 700, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: submitting || !name || !password || !confirm ? 0.6 : 1, boxShadow: '0 2px 10px rgba(99,102,241,0.35)', marginTop: 4, transition: 'opacity 0.1s' }}>
        {submitting ? 'Creating account…' : 'Create account & log in'}
      </button>
    </form>
  )
}

export default function JoinPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ width: 48, height: 48, borderRadius: 13, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', boxShadow: '0 0 24px rgba(99,102,241,0.4)' }}>
            <Radio size={22} color="white" />
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
            You've been invited to
          </h1>
          <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)', marginTop: 4 }}>
            MummyTKT's Bias Pointer
          </p>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
            Set up your account to get started.
          </p>
        </div>
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: 28, boxShadow: 'var(--shadow)' }}>
          <Suspense fallback={<p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</p>}>
            <JoinForm />
          </Suspense>
        </div>
        <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-secondary)', marginTop: 16 }}>
          Already have an account? <a href="/login" style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>Log in</a>
        </p>
      </div>
    </div>
  )
}
