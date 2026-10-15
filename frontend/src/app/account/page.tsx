'use client'
import { useState, useEffect } from 'react'
import { Shield, Users, Link2, Copy, Check, Trash2, Eye, EyeOff, LogIn, Crown, Clock, UserPlus, Globe } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { useAuth } from '@/lib/auth'
import { API_BASE } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import { useTimezone, TIMEZONES, getOffsetStr } from '@/lib/timezone'

function authFetch(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers ?? {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) },
  })
}

// ── Setup form (shown when auth is not yet configured) ────────────────────────

function SetupForm({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError('')
    setSubmitting(true)
    try {
      const r = await fetch(`${API_BASE}/api/auth/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, name, password }),
      })
      if (!r.ok) {
        let msg = 'Setup failed'
        try { const err = await r.json(); msg = err.detail || msg } catch {}
        throw new Error(msg)
      }
      const { token } = await r.json()
      localStorage.setItem('mbp_token', token)
      onDone()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Setup failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Shield size={16} color="var(--accent-hover)" />
        <div>
          <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Set up authentication</h2>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Create your owner account to protect this platform</p>
        </div>
      </div>
      <div style={{ padding: 24 }}>
        <div style={{ marginBottom: 20, padding: '12px 16px', borderRadius: 9, background: 'var(--accent-bg)', border: '1px solid var(--accent)30', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          Once enabled, a password will be required to access this platform. You can invite subscribers later from this page.
        </div>
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 400 }}>
          <InputField label="Your name" value={name} onChange={setName} placeholder="Toyosi Adebowale" />
          <InputField label="Email address" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Password</label>
            <div style={{ position: 'relative' }}>
              <input type={showPw ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Min. 8 characters"
                style={{ width: '100%', padding: '10px 40px 10px 12px', borderRadius: 8, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
              />
              <button type="button" onClick={() => setShowPw(v => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}>
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <InputField label="Confirm password" type="password" value={confirm} onChange={setConfirm} placeholder="Repeat password" />
          {error && <div style={{ padding: '10px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>{error}</div>}
          <button type="submit" disabled={submitting || !email || !name || !password || !confirm}
            style={{ padding: '10px 20px', borderRadius: 9, fontSize: 13, fontWeight: 700, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: submitting ? 0.6 : 1, boxShadow: '0 2px 8px rgba(99,102,241,0.35)' }}>
            {submitting ? 'Setting up…' : 'Enable authentication'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Helper components ─────────────────────────────────────────────────────────

function InputField({ label, value, onChange, placeholder, type = 'text' }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string
}) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{ width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
      />
    </div>
  )
}

const PLAN_META: Record<string, { label: string; color: string }> = {
  TRIAL:   { label: 'Free Trial',    color: 'var(--text-muted)' },
  '30DAY': { label: '30 Days',       color: 'var(--accent-hover)' },
  '6MONTH':{ label: '6 Months',      color: '#10b981' },
  '9MONTH':{ label: '9 Months',      color: '#7c3aed' },
  '12MONTH':{ label: '12 Months',    color: '#f59e0b' },
  LIFETIME:{ label: 'Lifetime',      color: 'var(--bullish)' },
}

function planLabel(plan: string) { return PLAN_META[plan]?.label ?? plan }
function planColor(plan: string) { return PLAN_META[plan]?.color ?? 'var(--text-secondary)' }

// ── Subscribers section (owner only) ─────────────────────────────────────────

interface Subscriber {
  id: number; email: string; name: string; role: string; plan: string
  plan_expires_at: string | null; invite_used: number
  created_at: string; last_login_at: string | null
}

function SubscribersSection() {
  const { fmtDate } = useTimezone()
  const [users, setUsers] = useState<Subscriber[]>([])
  const [loading, setLoading] = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [invitePlan, setInvitePlan] = useState('30DAY')
  const [inviteDays, setInviteDays] = useState('30')
  const [inviteLink, setInviteLink] = useState('')
  const [copied, setCopied] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [showInviteForm, setShowInviteForm] = useState(false)

  const load = () => {
    authFetch('/api/auth/users').then(r => r.json()).then(d => {
      setUsers(d.filter((u: Subscriber) => u.role !== 'OWNER'))
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const createInvite = async () => {
    if (!inviteEmail) return
    setError('')
    setCreating(true)
    try {
      const r = await authFetch('/api/auth/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail, name: inviteName, plan: invitePlan, plan_days: Math.min(365, Math.max(1, parseInt(inviteDays, 10) || 30)) }),
      })
      if (!r.ok) {
        const err = await r.json()
        throw new Error(err.detail || 'Failed to create invite')
      }
      const { token } = await r.json()
      const link = `${window.location.origin}/join?token=${token}`
      setInviteLink(link)
      setInviteEmail('')
      setInviteName('')
      load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error')
    } finally {
      setCreating(false)
    }
  }

  const revoke = async (id: number) => {
    await authFetch(`/api/auth/users/${id}`, { method: 'DELETE' })
    setUsers(u => u.filter(x => x.id !== id))
  }

  const copyLink = async () => {
    await navigator.clipboard.writeText(inviteLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Users size={15} color="var(--accent-hover)" />
          <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Subscribers</h2>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>({users.length})</span>
        </div>
        <button onClick={() => setShowInviteForm(v => !v)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: showInviteForm ? 'var(--card-hover)' : 'var(--accent)', color: showInviteForm ? 'var(--text-secondary)' : 'white', border: 'none', cursor: 'pointer' }}>
          <UserPlus size={12} />
          {showInviteForm ? 'Cancel' : 'Invite subscriber'}
        </button>
      </div>

      {showInviteForm && (
        <div style={{ padding: 20, borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <InputField label="Email *" value={inviteEmail} onChange={setInviteEmail} placeholder="subscriber@example.com" type="email" />
            <InputField label="Name (optional)" value={inviteName} onChange={setInviteName} placeholder="John Doe" />
          </div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Access plan</label>
              <select value={invitePlan} onChange={e => setInvitePlan(e.target.value)}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none' }}>
                <option value="30DAY">30-day access</option>
                <option value="TRIAL">Trial (7 days)</option>
                <option value="LIFETIME">Lifetime access</option>
              </select>
            </div>
            {invitePlan !== 'LIFETIME' && (
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Days</label>
                <input
                  type="text" inputMode="numeric" pattern="[0-9]*"
                  value={inviteDays}
                  onChange={e => setInviteDays(e.target.value.replace(/\D/g, ''))}
                  style={{ width: 80, padding: '9px 12px', borderRadius: 8, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none' }} />
              </div>
            )}
          </div>
          {error && <div style={{ padding: '9px 12px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 12, marginBottom: 12 }}>{error}</div>}
          {inviteLink && (
            <div style={{ marginBottom: 12, padding: '10px 14px', borderRadius: 8, background: 'var(--bullish-bg)', border: '1px solid var(--bullish)30', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Link2 size={13} color="var(--bullish)" style={{ flexShrink: 0 }} />
              <span style={{ flex: 1, fontSize: 12, color: 'var(--text-primary)', fontFamily: 'monospace', wordBreak: 'break-all' }}>{inviteLink}</span>
              <button onClick={copyLink} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'var(--bullish-bg)', color: 'var(--bullish)', fontSize: 11, fontWeight: 600 }}>
                {copied ? <Check size={11} /> : <Copy size={11} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}
          <button onClick={createInvite} disabled={creating || !inviteEmail}
            style={{ padding: '9px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: creating || !inviteEmail ? 0.6 : 1 }}>
            {creating ? 'Generating…' : 'Generate invite link'}
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</div>
      ) : users.length === 0 ? (
        <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
          <UserPlus size={28} color="var(--text-muted)" style={{ margin: '0 auto 10px' }} />
          <p>No subscribers yet.</p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Generate an invite link to give someone access.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table" style={{ minWidth: 500 }}>
            <thead>
              <tr>
                <th>Name / Email</th>
                <th>Plan</th>
                <th>Joined</th>
                <th>Last seen</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{u.name || '—'}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{u.email}</div>
                    {!u.invite_used && !u.last_login_at && <span style={{ fontSize: 10, color: 'var(--warning)', fontWeight: 600 }}>Invite pending</span>}
                  </td>
                  <td><span style={{ fontSize: 12, fontWeight: 600, color: planColor(u.plan) }}>{planLabel(u.plan)}</span></td>
                  <td><span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{fmtDate(u.created_at)}</span></td>
                  <td><span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{u.last_login_at ? timeAgo(u.last_login_at) : '—'}</span></td>
                  <td>
                    <button onClick={() => revoke(u.id)}
                      style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 11, fontWeight: 600 }}>
                      <Trash2 size={11} /> Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AccountPage() {
  const { user, authEnabled, refresh, logout } = useAuth()
  const { fmtDate, timezone, setTimezone, abbr } = useTimezone()
  const [editName, setEditName] = useState('')
  const [curPw, setCurPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pwSaving, setPwSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [pwMsg, setPwMsg] = useState('')
  const [setupDone, setSetupDone] = useState(false)
  const [tzPreview, setTzPreview] = useState('')

  useEffect(() => {
    if (user) setEditName(user.name || '')
  }, [user])

  useEffect(() => {
    const tick = () => {
      setTzPreview(new Date().toLocaleTimeString('en-GB', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: timezone,
      }))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [timezone])

  const saveName = async () => {
    if (!editName.trim()) return
    setSaving(true)
    setMsg('')
    try {
      const r = await authFetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName }),
      })
      if (!r.ok) throw new Error((await r.json()).detail)
      await refresh()
      setMsg('Name updated')
      setTimeout(() => setMsg(''), 3000)
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : 'Error')
    } finally {
      setSaving(false)
    }
  }

  const savePassword = async () => {
    if (newPw !== confirmPw) { setPwMsg('Passwords do not match'); return }
    if (newPw.length < 8) { setPwMsg('Minimum 8 characters'); return }
    setPwSaving(true)
    setPwMsg('')
    try {
      const r = await authFetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: curPw, new_password: newPw }),
      })
      if (!r.ok) throw new Error((await r.json()).detail)
      setCurPw(''); setNewPw(''); setConfirmPw('')
      setPwMsg('Password updated')
      setTimeout(() => setPwMsg(''), 3000)
    } catch (e: unknown) {
      setPwMsg(e instanceof Error ? e.message : 'Error')
    } finally {
      setPwSaving(false)
    }
  }

  if (!authEnabled && !setupDone) {
    return (
      <>
        <TopBar title="Account" subtitle="Your sign-in details and access" />
        <main style={{ flex: 1, padding: '24px', maxWidth: 700, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <SetupForm onDone={() => { setSetupDone(true); window.location.reload() }} />
        </main>
      </>
    )
  }

  if (!user) {
    return (
      <>
        <TopBar title="Account" subtitle="Your sign-in details and access" />
        <main style={{ flex: 1, padding: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <LogIn size={32} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Sign in to manage your account.</p>
          </div>
        </main>
      </>
    )
  }

  return (
    <>
      <TopBar title="Account" subtitle="Your sign-in details and current access" />
      <main className="page-padded" style={{ flex: 1, padding: '24px', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Account details + Plan */}
        <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
          {/* Details */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
              <h2 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Account details</h2>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Your name, email and role</p>
            </div>
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Row icon="👤" label="Name">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input value={editName} onChange={e => setEditName(e.target.value)}
                    style={{ flex: 1, padding: '7px 10px', borderRadius: 7, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none' }}
                  />
                  <button onClick={saveName} disabled={saving || editName === user.name}
                    style={{ padding: '7px 12px', borderRadius: 7, fontSize: 12, fontWeight: 600, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: saving ? 0.6 : 1, whiteSpace: 'nowrap' }}>
                    {saving ? '…' : 'Save'}
                  </button>
                </div>
                {msg && <p style={{ fontSize: 11, color: msg.includes('Error') || msg.includes('error') ? 'var(--bearish)' : 'var(--bullish)', marginTop: 4 }}>{msg}</p>}
              </Row>
              <Row icon="✉️" label="Email">
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{user.email}</span>
              </Row>
              <Row icon="🏷️" label="Role">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {user.role === 'OWNER' && <Crown size={12} color="var(--warning)" />}
                  <span style={{ fontSize: 13, fontWeight: 600, color: user.role === 'OWNER' ? 'var(--warning)' : 'var(--text-primary)' }}>
                    {user.role === 'OWNER' ? 'Owner' : 'Subscriber'}
                  </span>
                </div>
              </Row>
            </div>
          </div>

          {/* Plan */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
              <h2 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Plan & access</h2>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Current subscription details</p>
            </div>
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Row icon="⚡" label="Plan">
                <span style={{ fontSize: 13, fontWeight: 700, color: planColor(user.plan) }}>{planLabel(user.plan)}</span>
              </Row>
              <Row icon="📅" label="Member since">
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{user.created_at ? fmtDate(user.created_at) : '—'}</span>
              </Row>
              {user.plan_expires_at && user.plan !== 'LIFETIME' && (
                <Row icon="⏳" label="Expires">
                  <span style={{ fontSize: 13, color: 'var(--warning)' }}>{fmtDate(user.plan_expires_at)}</span>
                </Row>
              )}
              <Row icon="🕐" label="Last login">
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  {user.last_login_at ? timeAgo(user.last_login_at) : 'Just now'}
                </span>
              </Row>
            </div>
          </div>
        </div>

        {/* Change password */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
            <h2 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Change password</h2>
          </div>
          <div style={{ padding: 20 }}>
            <div className="grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, maxWidth: 600 }}>
              <PasswordInput label="Current password" value={curPw} onChange={setCurPw} show={showPw} onToggle={() => setShowPw(v => !v)} />
              <PasswordInput label="New password" value={newPw} onChange={setNewPw} show={showPw} onToggle={() => setShowPw(v => !v)} />
              <PasswordInput label="Confirm new" value={confirmPw} onChange={setConfirmPw} show={showPw} onToggle={() => setShowPw(v => !v)} />
            </div>
            {pwMsg && (
              <p style={{ fontSize: 12, marginTop: 10, color: pwMsg.includes('Error') || pwMsg.includes('error') || pwMsg.includes('incorrect') ? 'var(--bearish)' : 'var(--bullish)' }}>{pwMsg}</p>
            )}
            <button onClick={savePassword} disabled={pwSaving || !curPw || !newPw || !confirmPw}
              style={{ marginTop: 14, padding: '9px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: pwSaving ? 0.6 : 1 }}>
              {pwSaving ? 'Saving…' : 'Save password'}
            </button>
          </div>
        </div>

        {/* Display preferences */}
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Globe size={14} color="var(--accent-hover)" />
            <div>
              <h2 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Display preferences</h2>
              <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>How times and dates appear across the dashboard</p>
            </div>
          </div>
          <div style={{ padding: 20 }}>
            <Row icon="🌍" label="Timezone">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <select
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                  style={{
                    padding: '9px 12px', borderRadius: 8, fontSize: 13,
                    background: 'var(--bg)', border: '1px solid var(--border)',
                    color: 'var(--text-primary)', outline: 'none', maxWidth: 420,
                    cursor: 'pointer',
                  }}
                >
                  {Array.from(new Set(TIMEZONES.map(z => z.region))).map(region => (
                    <optgroup key={region} label={region}>
                      {TIMEZONES.filter(z => z.region === region).map(z => (
                        <option key={z.zone} value={z.zone}>
                          {z.label} ({getOffsetStr(z.zone)})
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Clock size={12} color="var(--text-muted)" />
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Current time in {abbr}:{' '}
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>{tzPreview}</span>
                  </span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  Saved automatically. All timestamps on the dashboard will update immediately.
                </p>
              </div>
            </Row>
          </div>
        </div>

        {/* Subscribers — owner only */}
        {user.role === 'OWNER' && <SubscribersSection />}

        {/* Sign out */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button onClick={logout}
            style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9, fontSize: 13, fontWeight: 600, border: '1px solid var(--border)', background: 'var(--card)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Clock size={14} />
            Sign out
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Signed in as {user.email}</span>
        </div>

      </main>
    </>
  )
}

function Row({ icon, label, children }: { icon: string; label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
      <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</p>
        {children}
      </div>
    </div>
  )
}

function PasswordInput({ label, value, onChange, show, onToggle }: {
  label: string; value: string; onChange: (v: string) => void; show: boolean; onToggle: () => void
}) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</label>
      <div style={{ position: 'relative' }}>
        <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
          style={{ width: '100%', padding: '9px 36px 9px 10px', borderRadius: 7, fontSize: 13, background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box' }}
        />
        <button type="button" onClick={onToggle}
          style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0 }}>
          {show ? <EyeOff size={13} /> : <Eye size={13} />}
        </button>
      </div>
    </div>
  )
}
