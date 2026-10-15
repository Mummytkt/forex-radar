'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Radio, TrendingUp, Bell, BarChart2, Shield, ArrowRight, CheckCircle2,
  Moon, Sun, Clock, Brain, ShieldCheck, Home, Car, Plane, Palmtree, Zap,
} from 'lucide-react'
import { useTheme } from '@/lib/theme'

const PLANS = [
  { id: '30DAY',   label: '30 Days',   price: 10, monthly: 10, save: null, badge: null,           highlight: false },
  { id: '6MONTH',  label: '6 Months',  price: 48, monthly: 8,  save: 20,   badge: 'Save 20%',     highlight: false },
  { id: '9MONTH',  label: '9 Months',  price: 63, monthly: 7,  save: 30,   badge: 'Most Popular', highlight: true  },
  { id: '12MONTH', label: '12 Months', price: 72, monthly: 6,  save: 40,   badge: 'Best Value',   highlight: false },
]

const FEATURES = [
  { icon: TrendingUp, title: 'Daily + H4 Alignment',  body: 'Bias is only confirmed when the Daily and H4 timeframes agree — reducing noise and keeping you on the right side of the market.' },
  { icon: Bell,       title: 'Telegram Alerts',       body: 'A structured alert lands the moment all confirmation conditions are met. No app to install — it comes straight to your phone.' },
  { icon: BarChart2,  title: '30+ Instruments',       body: 'All major forex pairs, minors, crosses, gold, indices and select crypto — monitored continuously, 24 hours a day.' },
  { icon: Shield,     title: 'Rules-Based Engine',    body: 'No discretion, no emotion. Every signal follows a strict confirmation chain built on A-shape, V-shape and OC formations.' },
]

const INCLUDES = [
  'Daily + H4 bias confirmation alerts',
  'All 30+ forex majors, minors & metals',
  'Telegram delivery — instant, no app needed',
  'Full strategy & tutorial video library',
  'Live instrument monitoring dashboard',
]

const PILLARS = [
  {
    icon: Clock,
    title: 'Freedom to live',
    body: "The engine watches 30+ markets around the clock so you don't have to. Do the school run, hit the gym, show up for your 9–5, be present with family — and only step in when an alert says a setup is ready.",
  },
  {
    icon: ShieldCheck,
    title: 'Confidence to act',
    body: 'Trade what you can see, not what you feel. Every alert is backed by a Daily + H4 confirmation chain, so you always know which way the market is leaning before you ever risk a cent.',
  },
  {
    icon: Brain,
    title: 'Discipline that protects you',
    body: 'Beat overtrading at the root. No alert means no trade. A calm, rules-based rhythm replaces the urge to force positions — guarding both your account and your peace of mind.',
  },
]

const STEPS = [
  { n: '01', title: 'The engine scans 24/7', body: 'Every pair, every Daily and H4 close — monitored continuously in the background.' },
  { n: '02', title: 'An alert hits your Telegram', body: 'Only when the full confirmation chain aligns. Clear direction, clear reason.' },
  { n: '03', title: 'You check for your entry', body: 'Open your chart, look for your entry model at the level, size your risk.' },
  { n: '04', title: 'Back to your life', body: 'No screen-watching between alerts. The market works while you live.' },
]

// Reveal-on-scroll: adds .lp-in to any .lp-reveal element as it enters the viewport
function useReveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll('.lp-reveal'))
    if (!('IntersectionObserver' in window)) {
      els.forEach(el => el.classList.add('lp-in'))
      return
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('lp-in'); io.unobserve(e.target) } })
    }, { threshold: 0.15 })
    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])
}

// ── Animated hero scene: self-drawing equity chart + floating alert cards ──────
function HeroScene() {
  return (
    <div style={{ position: 'relative', maxWidth: 720, margin: '0 auto', padding: '0 8px' }}>
      {/* dawn / horizon glow behind the card */}
      <div className="lp-drift" aria-hidden style={{
        position: 'absolute', inset: '-40px -10px -20px', zIndex: 0,
        background: 'radial-gradient(60% 70% at 70% 30%, rgba(99,102,241,0.35), transparent 70%), radial-gradient(50% 60% at 25% 80%, rgba(236,72,153,0.22), transparent 70%)',
        filter: 'blur(8px)', borderRadius: 32,
      }} />

      {/* product card */}
      <div className="lp-rise" style={{
        position: 'relative', zIndex: 1,
        background: 'var(--card)', border: '1px solid var(--border)',
        borderRadius: 18, overflow: 'hidden',
        boxShadow: '0 30px 80px -20px rgba(0,0,0,0.45)',
      }}>
        {/* mock top bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 16px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ef4444' }} />
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#f59e0b' }} />
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#22c55e' }} />
          <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>MummyTKT&apos;s Bias Pointer</span>
          <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 600, color: 'var(--bullish)' }}>
            <span className="pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--bullish)' }} /> Live
          </span>
        </div>

        {/* self-drawing equity chart */}
        <div style={{ padding: '18px 16px 10px' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Cumulative bias accuracy</div>
          <svg viewBox="0 0 400 180" preserveAspectRatio="none" style={{ width: '100%', height: 170, display: 'block', marginTop: 6 }}>
            <defs>
              <linearGradient id="lpArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
              </linearGradient>
            </defs>
            {/* area fill */}
            <path d="M0,150 C60,132 90,140 130,104 S220,74 260,58 S340,30 400,16 L400,180 L0,180 Z" fill="url(#lpArea)" />
            {/* drawing line */}
            <path className="lp-draw-path" d="M0,150 C60,132 90,140 130,104 S220,74 260,58 S340,30 400,16"
              fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" />
            {/* endpoint glow */}
            <circle className="lp-glow" cx="398" cy="16" r="6" fill="var(--accent)" />
          </svg>
        </div>
      </div>

      {/* floating alert cards */}
      <div className="lp-float" style={{
        position: 'absolute', zIndex: 2, top: 30, right: -6, maxWidth: 230,
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
        padding: '10px 12px', boxShadow: '0 16px 40px -12px rgba(0,0,0,0.5)',
        backdropFilter: 'blur(6px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: 'var(--bullish)' }}>
          <CheckCircle2 size={14} /> BUY BIAS CONFIRMED
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>EUR/USD · Daily → H4 aligned</div>
      </div>

      <div className="lp-float-sl" style={{
        position: 'absolute', zIndex: 2, bottom: -14, left: -4, maxWidth: 220,
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
        padding: '10px 12px', boxShadow: '0 16px 40px -12px rgba(0,0,0,0.5)',
        backdropFilter: 'blur(6px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: 'var(--accent-hover)' }}>
          <Zap size={14} /> ENTRY CONFIRMATION
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3 }}>XAU/USD · H1 sweep at your level</div>
      </div>
    </div>
  )
}

// ── Floating lifestyle motifs for the freedom band ────────────────────────────
function FreedomScenery() {
  const chips = [
    { icon: Home,     label: 'Home',     cls: 'lp-float',    left: '8%',  top: '18%' },
    { icon: Car,      label: 'Freedom',  cls: 'lp-float-sl', left: '70%', top: '12%' },
    { icon: Plane,    label: 'Travel',   cls: 'lp-float',    left: '82%', top: '58%' },
    { icon: Palmtree, label: 'Rest',     cls: 'lp-float-sl', left: '16%', top: '62%' },
  ]
  return (
    <div aria-hidden style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
      {/* dawn horizon */}
      <div className="lp-drift" style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(70% 90% at 50% 120%, rgba(245,158,11,0.18), transparent 60%), radial-gradient(60% 80% at 20% -10%, rgba(99,102,241,0.18), transparent 60%)',
      }} />
      {chips.map(({ icon: Icon, label, cls, left, top }) => (
        <div key={label} className={cls} style={{
          position: 'absolute', left, top,
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: 0.55,
        }}>
          <div style={{
            width: 46, height: 46, borderRadius: 14,
            background: 'var(--card)', border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)',
          }}>
            <Icon size={20} color="var(--accent-hover)" />
          </div>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
        </div>
      ))}
    </div>
  )
}

export default function LandingPage() {
  const { theme, toggle } = useTheme()
  const [year, setYear] = useState(2026)
  useEffect(() => { setYear(new Date().getFullYear()) }, [])
  useReveal()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)', overflowX: 'hidden' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 40,
        borderBottom: '1px solid var(--border)', background: 'var(--surface)',
        padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 58,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 12px rgba(99,102,241,0.4)' }}>
            <Radio size={15} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, lineHeight: 1.2 }}>MummyTKT&apos;s</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', marginTop: 1 }}>Bias Pointer</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button onClick={toggle} style={{ width: 34, height: 34, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--card)', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
          <Link href="/login" style={{ padding: '8px 20px', borderRadius: 9, background: 'var(--accent)', color: 'white', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
            Sign In
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ textAlign: 'center', padding: '72px 24px 40px', maxWidth: 760, margin: '0 auto' }}>
        <div className="lp-rise" style={{
          display: 'inline-flex', alignItems: 'center', gap: 7, padding: '6px 14px', borderRadius: 99,
          background: 'var(--accent-bg)', border: '1px solid rgba(99,102,241,0.3)',
          fontSize: 12, fontWeight: 600, color: 'var(--accent-hover)', marginBottom: 26,
        }}>
          <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
          Engine monitoring 30+ markets · 24/7
        </div>
        <h1 className="lp-rise" style={{ fontSize: 'clamp(38px, 6.4vw, 60px)', fontWeight: 800, lineHeight: 1.08, marginBottom: 20, letterSpacing: '-0.02em' }}>
          Profitability starts here.<br />
          <span style={{ color: 'var(--accent)' }}>Know the direction. Trade with confidence.</span>
        </h1>
        <p className="lp-rise" style={{ fontSize: 17, color: 'var(--text-secondary)', lineHeight: 1.75, maxWidth: 560, margin: '0 auto 34px' }}>
          MummyTKT&apos;s Bias Pointer is a rules-based forex engine that confirms Daily + H4
          directional alignment and sends structured bias alerts straight to your Telegram.
          No screen-watching. No second-guessing. Just clarity — and the freedom to live
          while the market works for you.
        </p>
        <div className="lp-rise" style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 56 }}>
          <a href="#pricing" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '13px 30px', borderRadius: 11, background: 'var(--accent)', color: 'white', fontSize: 15, fontWeight: 700, textDecoration: 'none', boxShadow: '0 8px 28px rgba(99,102,241,0.4)' }}>
            Start trading with clarity <ArrowRight size={16} />
          </a>
          <Link href="/login" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '13px 30px', borderRadius: 11, border: '1px solid var(--border)', background: 'var(--card)', color: 'var(--text-primary)', fontSize: 15, fontWeight: 600, textDecoration: 'none' }}>
            Sign In
          </Link>
        </div>

        <HeroScene />
      </section>

      {/* Freedom band */}
      <section style={{ position: 'relative', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', background: 'var(--surface)', padding: '90px 24px', marginTop: 48, overflow: 'hidden' }}>
        <FreedomScenery />
        <div className="lp-reveal" style={{ position: 'relative', zIndex: 1, maxWidth: 680, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 'clamp(28px, 4.5vw, 40px)', fontWeight: 800, lineHeight: 1.15, marginBottom: 16, letterSpacing: '-0.02em' }}>
            Trading should fund your life —<br /><span style={{ color: 'var(--accent)' }}>not consume it.</span>
          </h2>
          <p style={{ fontSize: 16, color: 'var(--text-secondary)', lineHeight: 1.75, maxWidth: 560, margin: '0 auto' }}>
            You didn&apos;t come to the markets to be chained to a screen. You came for freedom —
            the time, the confidence, and the calm to build the life you actually want.
            The Bias Pointer hands you all three.
          </p>
        </div>

        <div className="lp-reveal" style={{ position: 'relative', zIndex: 1, maxWidth: 1000, margin: '48px auto 0', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 18 }}>
          {PILLARS.map(({ icon: Icon, title, body }) => (
            <div key={title} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 16, padding: '26px 22px' }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
                <Icon size={20} color="var(--accent-hover)" />
              </div>
              <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 9 }}>{title}</p>
              <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section style={{ maxWidth: 1000, margin: '0 auto', padding: '80px 24px 20px' }}>
        <div className="lp-reveal" style={{ textAlign: 'center', marginBottom: 44 }}>
          <h2 style={{ fontSize: 'clamp(26px, 4vw, 34px)', fontWeight: 800, marginBottom: 10, letterSpacing: '-0.02em' }}>
            Four quiet steps. Zero screen fatigue.
          </h2>
          <p style={{ fontSize: 15, color: 'var(--text-secondary)' }}>
            Here&apos;s your day on the Bias Pointer — it does the watching, you do the living.
          </p>
        </div>
        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16 }}>
          {STEPS.map(({ n, title, body }) => (
            <div key={n} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '22px 20px' }}>
              <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 12 }}>{n}</div>
              <p style={{ fontWeight: 700, fontSize: 14.5, marginBottom: 7 }}>{title}</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 940, margin: '0 auto', padding: '60px 24px 72px' }}>
        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px 20px' }}>
              <div style={{ width: 38, height: 38, borderRadius: 10, background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
                <Icon size={18} color="var(--accent-hover)" />
              </div>
              <p style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>{title}</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{ maxWidth: 940, margin: '0 auto', padding: '0 24px 80px' }}>
        <div className="lp-reveal" style={{ textAlign: 'center', marginBottom: 40 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 10 }}>Simple, transparent pricing</h2>
          <p style={{ fontSize: 15, color: 'var(--text-secondary)' }}>Choose the plan that works for you. No auto-renew, no surprises.</p>
        </div>

        <div className="lp-reveal" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '20px 28px', marginBottom: 24 }}>
          <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
            Everything included in all plans
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 28px' }}>
            {INCLUDES.map(item => (
              <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <CheckCircle2 size={13} color="var(--bullish)" />
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14 }}>
          {PLANS.map(plan => (
            <div key={plan.id} style={{
              background: plan.highlight ? 'var(--accent)' : 'var(--card)',
              border: `1px solid ${plan.highlight ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 14, padding: '24px 20px', display: 'flex', flexDirection: 'column',
              boxShadow: plan.highlight ? '0 8px 32px rgba(99,102,241,0.4)' : undefined, position: 'relative',
            }}>
              {plan.badge && (
                <div style={{ position: 'absolute', top: 14, right: 14, padding: '3px 10px', borderRadius: 99, background: plan.highlight ? 'rgba(255,255,255,0.2)' : 'var(--accent-bg)', color: plan.highlight ? 'white' : 'var(--accent-hover)', fontSize: 11, fontWeight: 700 }}>
                  {plan.badge}
                </div>
              )}
              <p style={{ fontSize: 14, fontWeight: 700, color: plan.highlight ? 'rgba(255,255,255,0.85)' : 'var(--text-secondary)', marginBottom: 12 }}>{plan.label}</p>
              <div style={{ marginBottom: 4 }}>
                <span style={{ fontSize: 38, fontWeight: 800, color: plan.highlight ? 'white' : 'var(--text-primary)' }}>${plan.price}</span>
                <span style={{ fontSize: 13, color: plan.highlight ? 'rgba(255,255,255,0.65)' : 'var(--text-muted)', marginLeft: 5 }}>total</span>
              </div>
              <p style={{ fontSize: 12, color: plan.highlight ? 'rgba(255,255,255,0.65)' : 'var(--text-muted)', marginBottom: 22 }}>
                ${plan.monthly}/month{plan.save ? ` · ${plan.save}% off` : ''}
              </p>
              <Link href={`/signup?plan=${plan.id}`} style={{ display: 'block', textAlign: 'center', padding: '10px 16px', borderRadius: 9, marginTop: 'auto', background: plan.highlight ? 'white' : 'var(--accent-bg)', color: plan.highlight ? 'var(--accent)' : 'var(--accent-hover)', fontSize: 13, fontWeight: 700, textDecoration: 'none' }}>
                Get started
              </Link>
            </div>
          ))}
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 24 }}>
          Access is granted manually after payment. You&apos;ll receive login credentials via email once confirmed.
        </p>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '24px', textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
        © {year} MummyTKT&apos;s Bias Pointer · For educational purposes only · Not financial advice
      </footer>
    </div>
  )
}
