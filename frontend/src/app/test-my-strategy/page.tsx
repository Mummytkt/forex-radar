'use client'
// "Test my strategy" (owner, 2026-11-25): the public page her bios link to. A trader, mentor or community lead
// explains their strategy; it lands in her Requests page and on Telegram. Facts only: what the tool does today,
// no profit promises.
import { useState } from 'react'
import { API_BASE } from '@/lib/api'

const PAINS = [
  ['⏳', 'Backtesting by hand takes weeks', 'So most traders skip it, rush it, or stop halfway through the year.'],
  ['🙈', 'Manual backtests lie to you', "We quietly skip the ugly entries and tell ourselves we wouldn't have taken them."],
  ['😰', 'Losing streaks feel like the end', "Without data, 4 losses in a row look like a broken strategy, even when they're normal."],
  ['📺', 'Glued to the screen', 'Watching every candle play out because you have no numbers to trust.'],
]
const STEPS = [
  ['1', 'Explain your strategy', 'Your entry rules in your own words: the levels you mark, what confirms an entry, your SL and TP.'],
  ['2', 'I turn it into a tool', 'Every entry is checked automatically across years of real price data, not by memory.'],
  ['3', 'You get your numbers', 'Win rate, total R, losses in a row and a monthly review for each entry type, with a chart picture of every trade so you confirm each one yourself.'],
]

export default function TestMyStrategy() {
  const [f, setF] = useState({ name: '', contact: '', role: 'trader', markets: '', timeframes: '', strategy: '', backtest_now: '', goal: '', website: '' })
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF(x => ({ ...x, [k]: e.target.value }))
  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    if (f.name.trim().length < 2 || f.contact.trim().length < 5) return setErr('Please add your name and a way to reach you.')
    if (f.strategy.trim().length < 30) return setErr('Please describe your strategy and entry rules in a few sentences.')
    setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/api/public/strategy-request`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f) })
      if (!r.ok) { setErr((await r.json().catch(() => ({}))).detail || 'Could not send. Please try again.'); return }
      setDone(true)
    } catch { setErr('Network error. Please try again.') } finally { setBusy(false) }
  }
  const field: React.CSSProperties = { width: '100%', padding: '11px 12px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--bg)',
    color: 'var(--text-primary)', fontSize: 14.5, fontFamily: 'inherit' }
  const label: React.CSSProperties = { display: 'grid', gap: 6, fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }
  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)', padding: '40px 16px 60px' }}>
      <div style={{ maxWidth: 880, margin: '0 auto', display: 'grid', gap: 36 }}>
        <header style={{ display: 'grid', gap: 12 }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, letterSpacing: 1.2, textTransform: 'uppercase', color: 'var(--accent)' }}>Strategy to data</span>
          <h1 style={{ fontSize: 'clamp(30px, 5vw, 46px)', lineHeight: 1.1, fontWeight: 900, margin: 0 }}>
            Know your strategy&apos;s numbers before you risk real money.
          </h1>
          <p style={{ fontSize: 17, lineHeight: 1.6, color: 'var(--text-secondary)', margin: 0, maxWidth: 680 }}>
            I build tools that test a trading strategy across years of charts in seconds, not weeks. You explain your rules once;
            every entry is checked, and you see each trade with your own eyes.
          </p>
        </header>

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
          {PAINS.map(([i, t, d]) => (
            <div key={t} style={{ border: '1px solid var(--border)', borderRadius: 14, padding: 16, background: 'var(--card)', display: 'grid', gap: 6 }}>
              <span style={{ fontSize: 24 }}>{i}</span><b style={{ fontSize: 15 }}>{t}</b>
              <span style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{d}</span>
            </div>
          ))}
        </section>

        <section style={{ display: 'grid', gap: 12 }}>
          <h2 style={{ fontSize: 24, margin: 0 }}>How it works</h2>
          {STEPS.map(([n, t, d]) => (
            <div key={n} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
              <span style={{ flexShrink: 0, width: 34, height: 34, borderRadius: '50%', display: 'grid', placeItems: 'center', fontWeight: 900,
                background: 'var(--accent)', color: 'white' }}>{n}</span>
              <div><b style={{ fontSize: 15.5 }}>{t}</b><p style={{ margin: '3px 0 0', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.55 }}>{d}</p></div>
            </div>
          ))}
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            A backtest shows how your rules played out on past charts. It isn&apos;t a promise of future profit, but it means you go live knowing what your normal wins, losses and losing streaks look like.
          </p>
        </section>

        <section style={{ border: '1px solid var(--border)', borderRadius: 18, padding: 'clamp(16px, 4vw, 28px)', background: 'var(--card)' }}>
          {done ? (
            <div style={{ display: 'grid', gap: 8, textAlign: 'center', padding: '20px 0' }}>
              <span style={{ fontSize: 40 }}>🎉</span>
              <h2 style={{ margin: 0 }}>Got it, thank you!</h2>
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>I&apos;ll read your strategy and reach out on the contact you gave.</p>
            </div>
          ) : (
            <form onSubmit={send} style={{ display: 'grid', gap: 14 }}>
              <h2 style={{ margin: 0, fontSize: 24 }}>Tell me your strategy</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
                <label style={label}>Your name<input style={field} value={f.name} onChange={set('name')} autoComplete="name" /></label>
                <label style={label}>Email, WhatsApp or Telegram<input style={field} value={f.contact} onChange={set('contact')} placeholder="so I can reach you" /></label>
                <label style={label}>You are a
                  <select style={field} value={f.role} onChange={set('role')}>
                    <option value="trader">Trader</option><option value="mentor">Mentor</option>
                    <option value="community">Community lead</option><option value="other">Other</option>
                  </select>
                </label>
                <label style={label}>Markets you trade<input style={field} value={f.markets} onChange={set('markets')} placeholder="e.g. EURUSD, gold, NAS100" /></label>
                <label style={label}>Timeframes<input style={field} value={f.timeframes} onChange={set('timeframes')} placeholder="e.g. H4 bias, M15 entries" /></label>
              </div>
              <label style={label}>Your strategy and entry rules
                <textarea style={{ ...field, minHeight: 150, resize: 'vertical' }} value={f.strategy} onChange={set('strategy')}
                  placeholder="What do you mark on the chart? What confirms an entry? Where does your stop loss go, and your take profit?" />
              </label>
              <label style={label}>How do you test it today? (optional)
                <textarea style={{ ...field, minHeight: 70, resize: 'vertical' }} value={f.backtest_now} onChange={set('backtest_now')} placeholder="By hand, not at all, a spreadsheet..." />
              </label>
              <label style={label}>What do you most want to know? (optional)
                <input style={field} value={f.goal} onChange={set('goal')} placeholder="e.g. which entry works best, my worst losing streak" />
              </label>
              <input type="text" tabIndex={-1} autoComplete="off" value={f.website} onChange={set('website')} aria-hidden
                style={{ position: 'absolute', left: -9999, width: 1, height: 1, opacity: 0 }} />
              {err && <div style={{ color: 'var(--bearish)', fontWeight: 700, fontSize: 13.5 }}>{err}</div>}
              <button type="submit" disabled={busy} style={{ padding: '13px 18px', borderRadius: 12, border: 'none', background: 'var(--accent)', color: 'white',
                fontWeight: 800, fontSize: 15.5, cursor: 'pointer' }}>{busy ? 'Sending…' : 'Send my strategy'}</button>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>I only use your details to talk to you about your strategy test.</p>
            </form>
          )}
        </section>
        <footer style={{ fontSize: 12.5, color: 'var(--text-muted)', textAlign: 'center' }}>
          Taiwo Damilola Mayowa · Designer · QA · AI · <a href="https://taiwo-damilola-mayowa.vercel.app" style={{ color: 'var(--accent)' }}>Portfolio</a>
        </footer>
      </div>
    </main>
  )
}
