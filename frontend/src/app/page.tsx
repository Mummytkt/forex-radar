'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Radio, TrendingUp, Bell, BarChart2, Shield, ArrowRight, CheckCircle2,
  Moon, Sun, Clock, Brain, ShieldCheck, Zap, ChevronDown,
} from 'lucide-react'
import { useTheme } from '@/lib/theme'
import TrackRecord from '@/components/TrackRecord'

const PLANS = [
  { id: '30DAY',   label: '30 Days',   price: 10, monthly: 10, save: null, badge: null,           highlight: false, color: '#3b82f6' },
  { id: '6MONTH',  label: '6 Months',  price: 48, monthly: 8,  save: 20,   badge: 'Save 20%',     highlight: false, color: '#10b981' },
  { id: '9MONTH',  label: '9 Months',  price: 63, monthly: 7,  save: 30,   badge: 'Most Popular', highlight: true,  color: '#7c3aed' },
  { id: '12MONTH', label: '12 Months', price: 72, monthly: 6,  save: 40,   badge: 'Best Value',   highlight: false, color: '#f59e0b' },
]

const FEATURES = [
  { icon: TrendingUp, color: '#6366f1', title: 'Daily + H4 Alignment',  body: 'Bias is only confirmed when the Daily and H4 timeframes agree — reducing noise and keeping you on the right side of the market.' },
  { icon: Bell,       color: '#10b981', title: 'Telegram Alerts',       body: 'A structured alert lands the moment all confirmation conditions are met. No app to install — it comes straight to your phone.' },
  { icon: BarChart2,  color: '#f59e0b', title: '30+ Instruments',       body: 'All major forex pairs, minors, crosses, gold, indices and select crypto — monitored continuously, 24 hours a day.' },
  { icon: Shield,     color: '#ec4899', title: 'Rules-Based Engine',    body: 'No discretion, no emotion. Every signal follows a strict confirmation chain built on A-shape, V-shape and OC formations.' },
]

const INCLUDES = [
  'Daily + H4 bias confirmation alerts',
  'All 30+ forex majors, minors & metals',
  'Telegram delivery — instant, no app needed',
  'Full strategy & tutorial video library',
  'Live instrument monitoring dashboard',
]

const PILLARS = [
  { icon: Clock,       color: '#10b981', title: 'Freedom to live',           body: "The engine watches 30+ markets around the clock so you don't have to. Do the school run, hit the gym, show up for your 9–5, be present with family — and only step in when an alert says a setup is ready." },
  { icon: ShieldCheck, color: '#3b82f6', title: 'Confidence to act',         body: 'Trade what you can see, not what you feel. Every alert is backed by a Daily + H4 confirmation chain, so you always know which way the market is leaning before you ever risk a cent.' },
  { icon: Brain,       color: '#a855f7', title: 'Discipline that protects you', body: 'Beat overtrading at the root. No alert means no trade. A calm, rules-based rhythm replaces the urge to force positions — guarding both your account and your peace of mind.' },
]

const STEPS = [
  { n: '01', color: '#6366f1', title: 'The engine scans 24/7', body: 'Every pair, every Daily and H4 close — monitored continuously in the background.' },
  { n: '02', color: '#f59e0b', title: 'An alert hits your Telegram', body: 'Only when the full confirmation chain aligns. Clear direction, clear reason.' },
  { n: '03', color: '#10b981', title: 'You check for your entry', body: 'Open your chart, look for your entry model at the level, size your risk.' },
  { n: '04', color: '#ec4899', title: 'Back to your life', body: 'No screen-watching between alerts. The market works while you live.' },
]

function useReveal() {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll('.lp-reveal'))
    if (!('IntersectionObserver' in window)) { els.forEach(el => el.classList.add('lp-in')); return }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('lp-in'); io.unobserve(e.target) } })
    }, { threshold: 0.15 })
    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])
}

// ── Faint dashboard-mockup background (greyscale product simulation) ──────────
function MiniBars({ bars, color }: { bars: number[]; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 5, height: 44, marginTop: 10 }}>
      {bars.map((h, i) => <div key={i} style={{ width: 13, height: `${h}%`, borderRadius: 4, background: color }} />)}
    </div>
  )
}
function MockPanel({ children, style, cls, bg, border }: { children: React.ReactNode; style: React.CSSProperties; cls?: string; bg: string; border: string }) {
  return (
    <div className={cls} style={{ position: 'absolute', borderRadius: 16, background: bg, border: `1px solid ${border}`, padding: 14, backdropFilter: 'blur(2px)', boxShadow: '0 20px 50px -24px rgba(0,0,0,0.5)', ...style }}>
      {children}
    </div>
  )
}
function BgDashboardSim({ dark }: { dark: boolean }) {
  const C = dark ? {
    base: 'linear-gradient(180deg, #0a0c12 0%, #0e1119 45%, #0b0d14 100%)',
    glow1: 'rgba(99,102,241,0.28)', glow2: 'radial-gradient(circle, rgba(245,158,11,0.16), rgba(236,72,153,0.12) 45%, transparent 72%)',
    panelBg: 'rgba(255,255,255,0.07)', panelBorder: 'rgba(255,255,255,0.14)',
    lbl: 'rgba(255,255,255,0.5)', big: 'rgba(255,255,255,0.72)',
    chart: 'rgba(165,180,252,0.7)', ring: 'rgba(255,255,255,0.1)',
    scrim: 'radial-gradient(64% 56% at 50% 44%, rgba(6,7,12,0.80) 0%, rgba(6,7,12,0.62) 55%, rgba(6,7,12,0.20) 100%)',
  } : {
    base: 'linear-gradient(180deg, #eef1f8 0%, #e6ebf5 45%, #eef1f8 100%)',
    glow1: 'rgba(99,102,241,0.16)', glow2: 'radial-gradient(circle, rgba(245,158,11,0.12), rgba(236,72,153,0.10) 45%, transparent 72%)',
    panelBg: 'rgba(255,255,255,0.82)', panelBorder: 'rgba(15,17,32,0.08)',
    lbl: 'rgba(15,17,32,0.45)', big: 'rgba(15,17,32,0.62)',
    chart: 'rgba(99,102,241,0.55)', ring: 'rgba(15,17,32,0.08)',
    scrim: 'radial-gradient(64% 56% at 50% 44%, rgba(238,241,248,0.84) 0%, rgba(238,241,248,0.66) 55%, rgba(238,241,248,0.12) 100%)',
  }
  const lbl: React.CSSProperties = { fontSize: 10, fontWeight: 600, color: C.lbl, letterSpacing: '0.04em', textTransform: 'uppercase' }
  const big: React.CSSProperties = { fontSize: 22, fontWeight: 800, color: C.big, marginTop: 4 }
  return (
    <div aria-hidden style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 0 }}>
      <div style={{ position: 'absolute', inset: 0, background: C.base }} />
      <div className="lp-drift" style={{ position: 'absolute', left: '-6%', top: '-8%', width: '46%', height: '55%', background: `radial-gradient(circle, ${C.glow1}, transparent 70%)`, filter: 'blur(36px)' }} />
      <div className="lp-drift" style={{ position: 'absolute', right: '-8%', bottom: '-12%', width: '52%', height: '58%', background: C.glow2, filter: 'blur(40px)' }} />
      <div className="lp-drift" style={{ position: 'absolute', left: '28%', top: '34%', width: '44%', height: '48%', background: `radial-gradient(circle, ${dark ? 'rgba(16,185,129,0.14)' : 'rgba(16,185,129,0.10)'}, transparent 70%)`, filter: 'blur(44px)' }} />

      {/* floating dashboard mock panels (desktop) */}
      <div className="desktop-only" style={{ position: 'absolute', inset: 0 }}>
        <MockPanel cls="lp-float" bg={C.panelBg} border={C.panelBorder} style={{ left: '4%', top: '14%', width: 190, transform: 'rotate(-3deg)' }}>
          <div style={lbl}>Analytics</div>
          <div style={big}>$242.63</div>
          <MiniBars bars={[64, 42, 80, 52, 70, 48]} color={C.chart} />
        </MockPanel>

        <MockPanel cls="lp-float-sl" bg={C.panelBg} border={C.panelBorder} style={{ right: '5%', top: '12%', width: 210, transform: 'rotate(2deg)' }}>
          <div style={lbl}>Statistics</div>
          <div style={big}>+18.4%</div>
          <svg viewBox="0 0 180 54" style={{ width: '100%', height: 48, marginTop: 8 }}>
            <polyline points="0,44 30,36 60,40 90,22 120,28 150,12 180,16" fill="none" stroke={C.chart} strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        </MockPanel>

        <MockPanel cls="lp-float" bg={C.panelBg} border={C.panelBorder} style={{ left: '7%', bottom: '12%', width: 170, transform: 'rotate(2deg)', display: 'flex', alignItems: 'center', gap: 14 }}>
          <svg viewBox="0 0 52 52" style={{ width: 52, height: 52, flexShrink: 0 }}>
            <circle cx="26" cy="26" r="21" fill="none" stroke={C.ring} strokeWidth="6" />
            <circle cx="26" cy="26" r="21" fill="none" stroke={C.chart} strokeWidth="6" strokeDasharray="132" strokeDashoffset="20" transform="rotate(-90 26 26)" strokeLinecap="round" />
          </svg>
          <div>
            <div style={lbl}>Accuracy</div>
            <div style={{ ...big, fontSize: 18 }}>85%</div>
          </div>
        </MockPanel>

        <MockPanel cls="lp-float-sl" bg={C.panelBg} border={C.panelBorder} style={{ right: '6%', bottom: '14%', width: 190, transform: 'rotate(-2deg)' }}>
          <div style={lbl}>Win rate</div>
          <MiniBars bars={[50, 72, 44, 86, 60, 78]} color={C.chart} />
        </MockPanel>
      </div>

      {/* readability scrim — dark/light at centre (behind text), clear at edges (panels show) */}
      <div style={{ position: 'absolute', inset: 0, background: C.scrim }} />
    </div>
  )
}

// Animated product scene: self-drawing equity chart + floating alert cards
function HeroScene() {
  return (
    <div style={{ position: 'relative', maxWidth: 680, margin: '0 auto', padding: '0 8px' }}>
      <div className="lp-rise" style={{ position: 'relative', zIndex: 1, background: 'rgba(16,18,30,0.78)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 18, overflow: 'hidden', boxShadow: '0 30px 80px -20px rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 16px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ef4444' }} />
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#f59e0b' }} />
          <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#22c55e' }} />
          <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.7)' }}>MummyTKT&apos;s Bias Pointer</span>
          <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 600, color: '#4ade80' }}>
            <span className="pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ade80' }} /> Live
          </span>
        </div>
        <div style={{ padding: '18px 16px 10px' }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Cumulative bias accuracy</div>
          <svg viewBox="0 0 400 180" preserveAspectRatio="none" style={{ width: '100%', height: 170, display: 'block', marginTop: 6 }}>
            <defs>
              <linearGradient id="lpArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#818cf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d="M0,150 C60,132 90,140 130,104 S220,74 260,58 S340,30 400,16 L400,180 L0,180 Z" fill="url(#lpArea)" />
            <path className="lp-draw-path" d="M0,150 C60,132 90,140 130,104 S220,74 260,58 S340,30 400,16" fill="none" stroke="#818cf8" strokeWidth="3" strokeLinecap="round" />
            <circle className="lp-glow" cx="398" cy="16" r="6" fill="#a5b4fc" />
          </svg>
        </div>
      </div>

      <div className="lp-float" style={{ position: 'absolute', zIndex: 2, top: 26, right: -6, maxWidth: 230, background: 'rgba(16,18,30,0.92)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 12, padding: '10px 12px', boxShadow: '0 16px 40px -12px rgba(0,0,0,0.6)', backdropFilter: 'blur(6px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: '#4ade80' }}>
          <CheckCircle2 size={14} /> BUY BIAS CONFIRMED
        </div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.65)', marginTop: 3 }}>EUR/USD · Daily → H4 aligned</div>
      </div>

      <div className="lp-float-sl" style={{ position: 'absolute', zIndex: 2, bottom: -14, left: -4, maxWidth: 220, background: 'rgba(16,18,30,0.92)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 12, padding: '10px 12px', boxShadow: '0 16px 40px -12px rgba(0,0,0,0.6)', backdropFilter: 'blur(6px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: '#a5b4fc' }}>
          <Zap size={14} /> ENTRY CONFIRMATION
        </div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.65)', marginTop: 3 }}>XAU/USD · H1 sweep at your level</div>
      </div>
    </div>
  )
}

export default function LandingPage() {
  const { theme, toggle } = useTheme()
  const [year, setYear] = useState(2026)
  useEffect(() => { setYear(new Date().getFullYear()) }, [])
  useReveal()

  const dark = theme === 'dark'
  const P = dark ? {
    band: '#0a0c12', title: '#fff', accent: '#a5b4fc', body: 'rgba(255,255,255,0.78)',
    badgeBg: 'rgba(99,102,241,0.18)', badgeBorder: 'rgba(129,140,248,0.4)', badgeText: '#c7d2fe',
    pillarBg: 'rgba(16,18,30,0.6)', pillarBorder: 'rgba(255,255,255,0.1)', pillarIconBg: 'rgba(99,102,241,0.18)', pillarIcon: '#a5b4fc', pillarTitle: '#fff', pillarBody: 'rgba(255,255,255,0.65)',
    signinBg: 'rgba(255,255,255,0.06)', signinBorder: 'rgba(255,255,255,0.22)', signinText: '#fff',
    scroll: 'rgba(255,255,255,0.4)',
  } : {
    band: '#eef1f8', title: '#0f1120', accent: 'var(--accent)', body: '#48515f',
    badgeBg: 'rgba(99,102,241,0.1)', badgeBorder: 'rgba(99,102,241,0.3)', badgeText: 'var(--accent)',
    pillarBg: '#ffffff', pillarBorder: 'rgba(15,17,32,0.08)', pillarIconBg: 'var(--accent-bg)', pillarIcon: 'var(--accent-hover)', pillarTitle: '#0f1120', pillarBody: '#48515f',
    signinBg: '#ffffff', signinBorder: 'rgba(15,17,32,0.14)', signinText: '#0f1120',
    scroll: 'rgba(15,17,32,0.4)',
  }
  const heroTitle: React.CSSProperties = { textShadow: dark ? '0 2px 30px rgba(0,0,0,0.55)' : 'none' }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)', overflowX: 'clip' }}>

      {/* Nav */}
      <nav style={{ position: 'sticky', top: 0, zIndex: 40, borderBottom: '1px solid var(--border)', background: 'var(--surface)', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 58 }}>
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
          <Link href="/login" style={{ padding: '8px 20px', borderRadius: 9, background: 'var(--accent)', color: 'white', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>Sign In</Link>
        </div>
      </nav>

      {/* Scenic band: freedom hero (fills first screen) + pillars + profitability */}
      <div style={{ position: 'relative', background: P.band }}>
        <BgDashboardSim dark={dark} />

        {/* 1 — Freedom hero, sized to fill the first view */}
        <section style={{ position: 'relative', zIndex: 2, minHeight: 'calc(100vh - 58px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '56px 24px 40px', maxWidth: 840, margin: '0 auto' }}>
          <div className="lp-rise" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '6px 14px', borderRadius: 99, background: P.badgeBg, border: `1px solid ${P.badgeBorder}`, fontSize: 12, fontWeight: 600, color: P.badgeText, marginBottom: 28 }}>
            <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
            Engine monitoring 30+ markets · 24/7
          </div>
          <h1 className="lp-rise" style={{ ...heroTitle, fontSize: 'clamp(40px, 7vw, 68px)', fontWeight: 800, lineHeight: 1.06, marginBottom: 24, letterSpacing: '-0.02em', color: P.title }}>
            Trading should fund your life —<br /><span className="lp-grad1">not consume it.</span>
          </h1>
          <p className="lp-rise" style={{ fontSize: 18, color: P.body, lineHeight: 1.75, maxWidth: 600, margin: '0 auto 38px' }}>
            You didn&apos;t come to the markets to be chained to a screen. You came for freedom —
            the time, the confidence, and the calm to build the life you actually want.
            The Bias Pointer hands you all three.
          </p>
          <div className="lp-rise" style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
            <a href="#pricing" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '14px 32px', borderRadius: 11, background: 'var(--accent)', color: 'white', fontSize: 15, fontWeight: 700, textDecoration: 'none', boxShadow: '0 8px 28px rgba(99,102,241,0.5)' }}>
              Start trading with clarity <ArrowRight size={16} />
            </a>
            <Link href="/login" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '14px 32px', borderRadius: 11, border: `1px solid ${P.signinBorder}`, background: P.signinBg, color: P.signinText, fontSize: 15, fontWeight: 600, textDecoration: 'none', backdropFilter: 'blur(4px)' }}>
              Sign In
            </Link>
          </div>
          {/* scroll cue */}
          <div className="lp-float" style={{ marginTop: 54, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, color: P.scroll }}>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Scroll</span>
            <ChevronDown size={18} />
          </div>
        </section>

        {/* 2 — Pillars, directly under the freedom headline */}
        <section style={{ position: 'relative', zIndex: 2, maxWidth: 1000, margin: '0 auto', padding: '20px 24px 120px' }}>
          <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 18 }}>
            {PILLARS.map(({ icon: Icon, title, body, color }) => (
              <div key={title} className="lp-pop" style={{ background: `${color}1f`, border: `1px solid ${color}55`, borderRadius: 18, padding: '26px 22px', backdropFilter: 'blur(6px)', boxShadow: `0 18px 44px -24px ${color}` }}>
                <div style={{ width: 46, height: 46, borderRadius: 13, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16, boxShadow: `0 8px 20px -6px ${color}` }}>
                  <Icon size={21} color="#fff" />
                </div>
                <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 9, color: P.pillarTitle }}>{title}</p>
                <p style={{ fontSize: 13.5, color: P.pillarBody, lineHeight: 1.7 }}>{body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 3 — Profitability + animated scene (reached after a scroll) */}
        <section style={{ position: 'relative', zIndex: 2, textAlign: 'center', padding: '40px 24px 110px', maxWidth: 760, margin: '0 auto' }}>
          <h2 className="lp-reveal" style={{ ...heroTitle, fontSize: 'clamp(30px, 5vw, 46px)', fontWeight: 800, lineHeight: 1.12, marginBottom: 16, letterSpacing: '-0.02em', color: P.title }}>
            Profitability starts here.<br /><span className="lp-grad2">Know the direction. Trade with confidence.</span>
          </h2>
          <p className="lp-reveal" style={{ fontSize: 16, color: P.body, lineHeight: 1.75, maxWidth: 580, margin: '0 auto 52px' }}>
            MummyTKT&apos;s Bias Pointer is a rules-based forex engine that confirms Daily + H4
            directional alignment and sends structured bias alerts straight to your Telegram.
            No screen-watching. No second-guessing. Just clarity — and the freedom to live
            while the market works for you.
          </p>
          <div className="lp-reveal"><HeroScene /></div>
        </section>
      </div>

      {/* 4 — How it works */}
      <section style={{ maxWidth: 1000, margin: '0 auto', padding: '84px 24px 20px' }}>
        <div className="lp-reveal" style={{ textAlign: 'center', marginBottom: 44 }}>
          <h2 style={{ fontSize: 'clamp(26px, 4vw, 34px)', fontWeight: 800, marginBottom: 10, letterSpacing: '-0.02em' }}>Four quiet steps. Zero screen fatigue.</h2>
          <p style={{ fontSize: 15, color: 'var(--text-secondary)' }}>Here&apos;s your day on the Bias Pointer — it does the watching, you do the living.</p>
        </div>
        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16 }}>
          {STEPS.map(({ n, title, body, color }) => (
            <div key={n} className="lp-pop" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '22px 20px', borderTop: `3px solid ${color}` }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 34, height: 34, borderRadius: 9, background: `${color}22`, color, fontSize: 13, fontWeight: 800, marginBottom: 12 }}>{n}</div>
              <p style={{ fontWeight: 700, fontSize: 14.5, marginBottom: 7 }}>{title}</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 5 — Features */}
      <section style={{ maxWidth: 940, margin: '0 auto', padding: '60px 24px 72px' }}>
        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          {FEATURES.map(({ icon: Icon, title, body, color }) => (
            <div key={title} className="lp-pop" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '24px 20px' }}>
              <div style={{ width: 40, height: 40, borderRadius: 11, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14, boxShadow: `0 8px 20px -6px ${color}` }}>
                <Icon size={19} color="#fff" />
              </div>
              <p style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>{title}</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 5b — Public track record */}
      <TrackRecord />

      {/* 6 — Pricing */}
      <section id="pricing" style={{ maxWidth: 940, margin: '0 auto', padding: '0 24px 80px' }}>
        <div className="lp-reveal" style={{ textAlign: 'center', marginBottom: 40 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, marginBottom: 10 }}>Simple, transparent pricing</h2>
          <p style={{ fontSize: 15, color: 'var(--text-secondary)' }}>Choose the plan that works for you. No auto-renew, no surprises.</p>
        </div>

        <div className="lp-reveal" style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '20px 28px', marginBottom: 24 }}>
          <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>Everything included in all plans</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 28px' }}>
            {INCLUDES.map(item => (
              <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <CheckCircle2 size={13} color="var(--bullish)" />
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lp-reveal" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 16 }}>
          {PLANS.map(plan => (
            <div key={plan.id} className="lp-pop" style={{
              background: `${plan.color}1f`, border: `${plan.highlight ? 2 : 1}px solid ${plan.color}${plan.highlight ? 'aa' : '55'}`,
              borderRadius: 18, padding: '26px 22px', display: 'flex', flexDirection: 'column',
              boxShadow: `0 18px 44px -24px ${plan.color}`, position: 'relative',
            }}>
              {plan.badge && (
                <div style={{ position: 'absolute', top: 14, right: 14, padding: '3px 10px', borderRadius: 99, background: `${plan.color}2e`, color: plan.color, fontSize: 11, fontWeight: 700 }}>{plan.badge}</div>
              )}
              <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12 }}>{plan.label}</p>
              <div style={{ marginBottom: 4 }}>
                <span style={{ fontSize: 40, fontWeight: 800, color: plan.color }}>${plan.price}</span>
                <span style={{ fontSize: 13, color: 'var(--text-muted)', marginLeft: 5 }}>total</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 22 }}>${plan.monthly}/month{plan.save ? ` · ${plan.save}% off` : ''}</p>
              <Link href={`/checkout?plan=${plan.id}`} style={{ display: 'block', textAlign: 'center', padding: '11px 16px', borderRadius: 10, marginTop: 'auto', background: plan.color, color: '#fff', fontSize: 13, fontWeight: 800, textDecoration: 'none' }}>Get started</Link>
            </div>
          ))}
        </div>

        {/* Free trial CTA */}
        <div className="lp-reveal lp-pop" style={{
          marginTop: 20, borderRadius: 18, padding: '22px 24px',
          background: 'linear-gradient(100deg, #ec489922, #a855f722)', border: '1px solid #ec489955',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap',
          boxShadow: '0 18px 44px -26px #ec4899',
        }}>
          <div>
            <p style={{ fontWeight: 800, fontSize: 17, marginBottom: 4 }}>Not ready to commit? <span className="lp-grad3">Try it free for 7 days.</span></p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Full access, no charge for a week. Keep it and you&apos;re billed $10/month after — cancel anytime.
            </p>
          </div>
          <Link href="/checkout?plan=TRIAL" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '12px 24px', borderRadius: 11, background: '#ec4899', color: '#fff', fontSize: 14, fontWeight: 800, textDecoration: 'none', whiteSpace: 'nowrap' }}>
            Start free trial <ArrowRight size={16} />
          </Link>
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 24 }}>
          Secure checkout by Paystack. Access is activated automatically the moment your payment confirms.
        </p>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '24px', textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', lineHeight: 2 }}>
        <nav aria-label="Legal" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '4px 18px', marginBottom: 6 }}>
          {[['/terms', 'Terms'], ['/privacy', 'Privacy'], ['/refunds', 'Refunds & Cancellation'], ['/risk', 'Risk Disclaimer']].map(([href, label]) => (
            <a key={href} href={href} style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 }}>{label}</a>
          ))}
          <a href="mailto:olaomidamilola@gmail.com" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 }}>Contact</a>
        </nav>
        © {year} MummyTKT&apos;s Bias Pointer · For educational purposes only · Not financial advice
      </footer>
    </div>
  )
}
