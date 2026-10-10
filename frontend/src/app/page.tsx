'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Radio, TrendingUp, Bell, BarChart2, Shield,
  ArrowRight, CheckCircle2, Moon, Sun,
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
  { icon: Bell,       title: 'Telegram Alerts',        body: 'Receive a structured alert the moment all 4 confirmation conditions are met. No app required — just your phone.' },
  { icon: BarChart2,  title: '30+ Instruments',        body: 'All major forex pairs, minors, crosses, gold, and select crypto monitored continuously — 24 hours a day.' },
  { icon: Shield,     title: 'Rules-Based Engine',     body: 'No discretion, no emotion. Every signal follows a strict 4-step confirmation chain built on A-shape, V-shape, and OC formations.' },
]

const INCLUDES = [
  'Daily + H4 bias confirmation alerts',
  'All 30+ forex majors, minors & metals',
  'Telegram delivery — instant, no app needed',
  'Full strategy & tutorial video library',
  'Live instrument monitoring dashboard',
]

export default function LandingPage() {
  const { theme, toggle } = useTheme()
  const [year, setYear] = useState(2026)
  useEffect(() => { setYear(new Date().getFullYear()) }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)' }}>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 40,
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        padding: '0 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: 58,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 9,
            background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 12px rgba(99,102,241,0.4)',
          }}>
            <Radio size={15} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.2 }}>MummyTKT&apos;s</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', marginTop: 1 }}>Bias Pointer</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button onClick={toggle} style={{
            width: 34, height: 34, borderRadius: 8, border: '1px solid var(--border)',
            background: 'var(--card)', color: 'var(--text-secondary)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>
          <Link href="/login" style={{
            padding: '8px 20px', borderRadius: 9,
            background: 'var(--accent)', color: 'white',
            fontSize: 13, fontWeight: 600, textDecoration: 'none',
            display: 'inline-block',
          }}>
            Sign In
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ textAlign: 'center', padding: '80px 24px 64px', maxWidth: 680, margin: '0 auto' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 7,
          padding: '6px 14px', borderRadius: 99,
          background: 'var(--accent-bg)', border: '1px solid rgba(99,102,241,0.3)',
          fontSize: 12, fontWeight: 600, color: 'var(--accent-hover)',
          marginBottom: 28,
        }}>
          <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
          Engine monitoring 24/7
        </div>
        <h1 style={{
          fontSize: 'clamp(36px, 6vw, 54px)', fontWeight: 800, lineHeight: 1.1,
          color: 'var(--text-primary)', marginBottom: 20, letterSpacing: '-0.02em',
        }}>
          Know the bias.<br />
          <span style={{ color: 'var(--accent)' }}>Trade with confidence.</span>
        </h1>
        <p style={{
          fontSize: 17, color: 'var(--text-secondary)', lineHeight: 1.7,
          maxWidth: 520, margin: '0 auto 36px',
        }}>
          MummyTKT&apos;s Bias Pointer is a rules-based forex analysis engine that confirms
          Daily + H4 directional alignment and delivers structured bias alerts straight
          to your Telegram.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
          <a href="#pricing" style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            padding: '12px 28px', borderRadius: 10,
            background: 'var(--accent)', color: 'white',
            fontSize: 14, fontWeight: 700, textDecoration: 'none',
            boxShadow: '0 4px 20px rgba(99,102,241,0.35)',
          }}>
            Get Started <ArrowRight size={15} />
          </a>
          <Link href="/login" style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            padding: '12px 28px', borderRadius: 10,
            border: '1px solid var(--border)',
            background: 'var(--card)', color: 'var(--text-primary)',
            fontSize: 14, fontWeight: 600, textDecoration: 'none',
          }}>
            Sign In
          </Link>
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 940, margin: '0 auto', padding: '0 24px 72px' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16,
        }}>
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} style={{
              background: 'var(--card)', border: '1px solid var(--border)',
              borderRadius: 14, padding: '24px 20px',
            }}>
              <div style={{
                width: 38, height: 38, borderRadius: 10,
                background: 'var(--accent-bg)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 14,
              }}>
                <Icon size={18} color="var(--accent-hover)" />
              </div>
              <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', marginBottom: 8 }}>{title}</p>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{ maxWidth: 940, margin: '0 auto', padding: '0 24px 80px' }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 10 }}>
            Simple, transparent pricing
          </h2>
          <p style={{ fontSize: 15, color: 'var(--text-secondary)' }}>
            Choose the plan that works for you. No auto-renew, no surprises.
          </p>
        </div>

        {/* Includes */}
        <div style={{
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: 14, padding: '20px 28px', marginBottom: 24,
        }}>
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

        {/* Plan cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14 }}>
          {PLANS.map(plan => (
            <div key={plan.id} style={{
              background: plan.highlight ? 'var(--accent)' : 'var(--card)',
              border: `1px solid ${plan.highlight ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 14, padding: '24px 20px',
              display: 'flex', flexDirection: 'column',
              boxShadow: plan.highlight ? '0 8px 32px rgba(99,102,241,0.4)' : undefined,
              position: 'relative',
            }}>
              {plan.badge && (
                <div style={{
                  position: 'absolute', top: 14, right: 14,
                  padding: '3px 10px', borderRadius: 99,
                  background: plan.highlight ? 'rgba(255,255,255,0.2)' : 'var(--accent-bg)',
                  color: plan.highlight ? 'white' : 'var(--accent-hover)',
                  fontSize: 11, fontWeight: 700,
                }}>
                  {plan.badge}
                </div>
              )}
              <p style={{ fontSize: 14, fontWeight: 700, color: plan.highlight ? 'rgba(255,255,255,0.85)' : 'var(--text-secondary)', marginBottom: 12 }}>
                {plan.label}
              </p>
              <div style={{ marginBottom: 4 }}>
                <span style={{ fontSize: 38, fontWeight: 800, color: plan.highlight ? 'white' : 'var(--text-primary)' }}>
                  ${plan.price}
                </span>
                <span style={{ fontSize: 13, color: plan.highlight ? 'rgba(255,255,255,0.65)' : 'var(--text-muted)', marginLeft: 5 }}>
                  total
                </span>
              </div>
              <p style={{ fontSize: 12, color: plan.highlight ? 'rgba(255,255,255,0.65)' : 'var(--text-muted)', marginBottom: 22 }}>
                ${plan.monthly}/month{plan.save ? ` · ${plan.save}% off` : ''}
              </p>
              <Link href={`/signup?plan=${plan.id}`} style={{
                display: 'block', textAlign: 'center',
                padding: '10px 16px', borderRadius: 9, marginTop: 'auto',
                background: plan.highlight ? 'white' : 'var(--accent-bg)',
                color: plan.highlight ? 'var(--accent)' : 'var(--accent-hover)',
                fontSize: 13, fontWeight: 700, textDecoration: 'none',
              }}>
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
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '24px',
        textAlign: 'center',
        fontSize: 12, color: 'var(--text-muted)',
      }}>
        © {year} MummyTKT&apos;s Bias Pointer · For educational purposes only · Not financial advice
      </footer>

    </div>
  )
}
