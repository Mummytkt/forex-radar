'use client'
import { useCallback, useEffect, useState } from 'react'
import { Briefcase, Send, CheckCircle2, Mic, Clock, Loader2, Plus } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useTimezone } from '@/lib/timezone'

// Owner only: the jobs the Job Hunt bot sent, and where each application stands (alerts/job_digest.py).
function api(path: string, opts: RequestInit = {}) {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { ...(opts.headers || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}), 'Content-Type': 'application/json' },
  })
}

interface App {
  id: number; url: string; source: string; title: string; company: string; location: string; region: string
  posted_at: string; sent_at: string; status: string; applied_at: string | null; follow_at: string | null; kind?: string
}

const KINDS: [string, string][] = [['job', 'Job'], ['freelance', 'Freelance proposal'], ['fiverr', 'Fiverr order'], ['client', 'Client lead']]
const SOURCES = ['LinkedIn', 'Jobberman', 'MyJobMag', 'Indeed', 'Upwork', 'Fiverr', 'Contra', 'Company website', 'Referral', 'Other']
const field: React.CSSProperties = {
  padding: '8px 10px', borderRadius: 8, fontSize: 13, border: '1px solid var(--border)', background: 'var(--bg)',
  color: 'var(--text-primary)', outline: 'none', minWidth: 0,
}

const STATUS: [string, string, string][] = [
  ['new', 'New', 'var(--text-secondary)'],
  ['applied', 'Applied', '#60a5fa'],
  ['followed_up', 'Followed up', '#a78bfa'],
  ['interview', 'Interview', '#22c55e'],
  ['offer', 'Offer', '#eab308'],
  ['rejected', 'Rejected', 'var(--bearish)'],
  ['no_reply', 'No reply', 'var(--text-muted)'],
  ['skipped', 'Skipped', 'var(--text-muted)'],
]
const LABEL = Object.fromEntries(STATUS.map(([k, l]) => [k, l]))
const COLOR = Object.fromEntries(STATUS.map(([k, , c]) => [k, c]))
const TABS: [string, string, string[]][] = [
  ['review', 'To review', ['new']],
  ['active', 'In progress', ['applied', 'followed_up', 'interview', 'offer']],
  ['closed', 'Closed', ['rejected', 'no_reply', 'skipped']],
  ['all', 'All', []],
]

const card: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12 }

function Tile({ icon: Icon, label, value, note }: { icon: React.ElementType; label: string; value: number | string; note?: string }) {
  return (
    <div style={{ ...card, padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>
        <Icon size={13} color="var(--accent-hover)" /> {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {note && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{note}</div>}
    </div>
  )
}

export default function JobHuntPage() {
  const { user } = useAuth()
  const { fmtDate } = useTimezone()
  const [apps, setApps] = useState<App[] | null>(null)
  const [botOn, setBotOn] = useState(true)
  const [tab, setTab] = useState('review')
  const [error, setError] = useState('')
  const [run, setRun] = useState<{ busy: boolean; msg?: string }>({ busy: false })
  const [goal, setGoal] = useState<{ interviews: number; by: string }>({ interviews: 5, by: '2026-12-24' })
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ title: '', company: '', url: '', source: 'LinkedIn', kind: 'job' })
  const [formErr, setFormErr] = useState('')
  const [now, setNow] = useState('')   // set after load (a clock read can't happen while the page is pre-built)

  const load = useCallback(() => {
    api('/api/jobs/apps').then(r => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(d => { setApps(d.apps); setBotOn(d.bot_on); if (d.goal) setGoal(d.goal); setNow(new Date().toISOString()) })
      .catch(() => setError("Couldn't load your applications. Refresh to try again."))
  }, [])
  useEffect(() => { if (user?.role === 'OWNER') load() }, [user, load])

  const change = async (id: number, status: string) => {
    setApps(a => a && a.map(x => (x.id === id ? { ...x, status } : x)))
    const r = await api(`/api/jobs/apps/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
    if (r.ok) { const n = await r.json(); setApps(a => a && a.map(x => (x.id === id ? n : x))) } else load()
  }

  const changeKind = async (id: number, kind: string) => {
    setApps(a => a && a.map(x => (x.id === id ? { ...x, kind } : x)))
    const r = await api(`/api/jobs/apps/${id}`, { method: 'PATCH', body: JSON.stringify({ kind }) })
    if (!r.ok) load()
  }

  const addApp = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormErr('')
    if (!form.title.trim()) { setFormErr('Give the job a title.'); return }
    const r = await api('/api/jobs/apps', { method: 'POST', body: JSON.stringify(form) })
    if (!r.ok) { setFormErr("Couldn't save it. Try again."); return }
    setForm({ title: '', company: '', url: '', source: form.source, kind: form.kind })
    setAdding(false)
    setTab('active')
    load()
  }

  const sendNow = async () => {
    setRun({ busy: true })
    try {
      const r = await api('/api/jobs/run', { method: 'POST' })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || 'Failed')
      setRun({ busy: false, msg: `Sent to your Job Hunt bot: ${d.sent} new job${d.sent === 1 ? '' : 's'}.` })
      load()
    } catch (e: unknown) {
      setRun({ busy: false, msg: e instanceof Error ? e.message : 'Failed' })
    }
  }

  if (user && user.role !== 'OWNER') {
    return (<><TopBar title="Job Hunt" subtitle="Owner only" /><main className="page-padded" style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 14 }}>This page is only available to the platform owner.</main></>)
  }

  const list = apps ?? []
  const count = (ks: string[]) => list.filter(a => ks.includes(a.status)).length
  const due = list.filter(a => ['applied', 'followed_up'].includes(a.status) && a.follow_at && now && a.follow_at <= now).length
  const interviews = count(['interview', 'offer'])
  const weekAgo = now ? new Date(new Date(now).getTime() - 7 * 86400000).toISOString() : ''
  const thisWeek = list.filter(a => a.applied_at && weekAgo && a.applied_at >= weekAgo).length
  const daysLeft = now ? Math.max(0, Math.ceil((new Date(goal.by + 'T23:59:59Z').getTime() - new Date(now).getTime()) / 86400000)) : null
  const shown = tab === 'all' ? list : list.filter(a => TABS.find(t => t[0] === tab)![2].includes(a.status))

  return (
    <>
      <TopBar title="Job Hunt" subtitle="Your remote job digest and every application, in one place" />
      <main className="page-padded" style={{ flex: 1, width: '100%', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {error && <div style={{ padding: '10px 14px', borderRadius: 8, background: 'var(--bearish-bg)', color: 'var(--bearish)', fontSize: 13 }}>{error}</div>}
        {!botOn && (
          <div style={{ ...card, padding: '14px 18px', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            <b style={{ color: 'var(--text-primary)' }}>The Job Hunt bot isn&apos;t connected yet.</b> Make a bot with @BotFather in Telegram,
            save its token on the server as JOBS_BOT_TOKEN, then press Start on the new bot. The digest then arrives every morning at 08:30 WAT.
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
          <Tile icon={Briefcase} label="To review" value={count(['new'])} />
          <Tile icon={CheckCircle2} label="Applied" value={count(['applied', 'followed_up', 'interview', 'offer', 'rejected', 'no_reply'])} />
          <Tile icon={Clock} label="Follow-ups due" value={due} />
          <Tile icon={Mic} label="Interviews by Christmas" value={`${interviews} of ${goal.interviews}`}
            note={daysLeft !== null ? `${daysLeft} days left · ${thisWeek} applied this week` : undefined} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {TABS.map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 12.5, fontWeight: 600, cursor: 'pointer', border: '1px solid',
              borderColor: tab === k ? 'var(--accent)' : 'var(--border)', background: tab === k ? 'var(--accent)' : 'var(--card)',
              color: tab === k ? 'white' : 'var(--text-secondary)',
            }}>{l}</button>
          ))}
          <div style={{ flex: 1 }} />
          <button onClick={() => setAdding(v => !v)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8, fontSize: 12.5, fontWeight: 600,
            cursor: 'pointer', border: '1px solid var(--accent)', background: adding ? 'var(--accent)' : 'var(--card)',
            color: adding ? 'white' : 'var(--accent-hover)',
          }}><Plus size={13} /> Add application</button>
          {botOn && (
            <button onClick={sendNow} disabled={run.busy} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8, fontSize: 12.5, fontWeight: 600,
              cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--card)', color: 'var(--text-primary)',
            }}>{run.busy ? <Loader2 size={13} className="spin" /> : <Send size={13} />} Check for new jobs now</button>
          )}
        </div>
        {adding && (
          <form onSubmit={addApp} style={{ ...card, padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
            <input style={field} placeholder="Job title (required)" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} aria-label="Job title" />
            <input style={field} placeholder="Company" value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} aria-label="Company" />
            <input style={field} placeholder="Link (optional)" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} aria-label="Link" />
            <select style={field} value={form.source} onChange={e => setForm({ ...form, source: e.target.value })} aria-label="Where you found it">
              {SOURCES.map(x => <option key={x} value={x}>{x}</option>)}
            </select>
            <select style={field} value={form.kind} onChange={e => setForm({ ...form, kind: e.target.value })} aria-label="Type">
              {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
            <button type="submit" style={{ ...field, background: 'var(--accent)', color: 'white', fontWeight: 700, cursor: 'pointer', border: 'none' }}>
              Save as applied
            </button>
            {formErr && <div style={{ gridColumn: '1 / -1', fontSize: 12.5, color: 'var(--bearish)' }}>{formErr}</div>}
            <div style={{ gridColumn: '1 / -1', fontSize: 11.5, color: 'var(--text-muted)' }}>
              Saved as Applied today; the bot asks how it went in 7 days. From Telegram: /add Title | Company | link
            </div>
          </form>
        )}
        {run.msg && <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{run.msg}</div>}
        <div style={{ ...card, overflow: 'hidden' }}>
          {apps === null ? (
            <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</div>
          ) : shown.length === 0 ? (
            <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>Nothing here yet.</div>
          ) : shown.map(a => (
            <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 260px', minWidth: 0 }}>
                <a href={a.url.startsWith('manual:') ? undefined : a.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--text-primary)', textDecoration: 'none' }}>{a.title}{a.url.startsWith('manual:') ? '' : ' ↗'}</a>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                  {a.company} · {a.region === 'EMEA' ? 'EMEA (check Africa)' : a.region} · {a.source} · sent {fmtDate(a.sent_at)}
                  {a.applied_at && <> · applied {fmtDate(a.applied_at)}</>}
                </div>
              </div>
              <select value={a.kind || 'job'} onChange={e => changeKind(a.id, e.target.value)} aria-label={`Type of ${a.title}`} style={{
                padding: '6px 10px', borderRadius: 8, fontSize: 12, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-secondary)',
              }}>
                {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
              <select value={a.status} onChange={e => change(a.id, e.target.value)} aria-label={`Status of ${a.title}`} style={{
                padding: '6px 10px', borderRadius: 8, fontSize: 12.5, fontWeight: 600, border: '1px solid var(--border)',
                background: 'var(--bg)', color: COLOR[a.status] || 'var(--text-primary)',
              }}>
                {STATUS.map(([k]) => <option key={k} value={k}>{LABEL[k]}</option>)}
              </select>
            </div>
          ))}
        </div>
      </main>
    </>
  )
}
