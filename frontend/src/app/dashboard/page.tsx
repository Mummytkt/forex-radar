'use client'
import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { Activity, Zap, Bell, BarChart2, TrendingUp, TrendingDown, ArrowRight, Shield, CheckCircle2, Circle, Wifi, WifiOff } from 'lucide-react'
import Link from 'next/link'
import TopBar from '@/components/TopBar'
import StatCard from '@/components/StatCard'
import { fetcher } from '@/lib/api'
import { useTimezone } from '@/lib/timezone'
import { useAuth } from '@/lib/auth'
import { useAccent } from '@/lib/useAccent'
import { PALETTE } from '@/lib/accent'
import type { Stats, AlertsPage } from '@/lib/types'
import OnboardingChecklist, { type Onboarding } from '@/components/OnboardingChecklist'
import LiveChartBoard from '@/components/LiveChartBoard'
import AlertTypeFilter, { useAlertTypes, typesQuery, typeLabel } from '@/components/AlertTypeFilter'

interface Profile {
  telegram_configured: boolean
  member_since: string | null
  first_alert_at: string | null
  total_alerts: number
  instruments_count: number
}

function fmtMemberSince(iso: string | null): string {
  if (!iso) return 'Early access'
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
}

function planLabel(plan?: string) {
  if (plan === 'LIFETIME') return 'Lifetime Access'
  if (plan === '30DAY') return '30-day Access'
  if (plan === 'TRIAL') return 'Trial Access'
  if (plan === 'TESTER') return 'Tester Access'
  return plan ?? '—'
}

export default function OverviewPage() {
  const [greeting, setGreeting] = useState('')
  const [today, setToday] = useState('')
  const { fmtDate } = useTimezone()
  const { user } = useAuth()
  const { data: stats } = useSWR<Stats>('/api/stats', fetcher, { refreshInterval: 30000 })
  const [alertTypes, setAlertTypes] = useAlertTypes()
  const { data: alerts } = useSWR<AlertsPage>('/api/alerts?limit=5' + typesQuery(alertTypes), fetcher, { refreshInterval: 30000 })
  const { data: profile } = useSWR<Profile>('/api/profile', fetcher, { refreshInterval: 60000 })
  const { data: onboarding } = useSWR<Onboarding>('/api/onboarding', fetcher, { refreshInterval: 60000 })

  useEffect(() => {
    const h = new Date().getHours()
    setGreeting(h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening')
    setToday(new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))
  }, [])

  const firstName = user?.name?.split(' ')[0] || user?.name || ''
  const { accent, setAccent } = useAccent()

  // Counts come from the charts' own view, sent by the Bias Pointer at every H4 close
  const { data: board } = useSWR<{ pairs: { instrument: string; snapshot: { stage: string } | null }[] }>('/api/chart-board', fetcher, { refreshInterval: 60000 })
  const stages = (board?.pairs ?? []).map(p => p.snapshot?.stage)
  const pairCount = board ? board.pairs.length : null
  const activeCount = board ? stages.filter(s => s && s !== 'idle').length : null
  const retestCount = board ? stages.filter(s => s === 'retest').length : null

  const isOwner = user?.role === 'OWNER'
  // This user's own Telegram link (not the platform's), so a subscriber who hasn't
  // linked Telegram is never told their alerts are active.
  const tgLinked = onboarding?.telegram_linked ?? false
  const steps = [
    { label: 'Engine running', done: true },
    { label: 'Instruments loaded', done: (pairCount ?? stats?.total_instruments ?? 0) > 0 },
    { label: 'Telegram linked', done: tgLinked },
    { label: 'First alert fired', done: (profile?.first_alert_at ?? null) !== null },
  ]

  return (
    <>
      <TopBar title="Bias Board" subtitle={today} />
      <main className="page-padded" style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* First-login setup checklist (subscribers) */}
        {!isOwner && user && onboarding && <OnboardingChecklist uid={user.id} data={onboarding} />}

        {/* Profile status banner */}
        <div style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          boxShadow: 'var(--shadow)',
          overflow: 'hidden',
        }}>
          {/* Top row: greeting + engine pulse */}
          <div style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
                {greeting}{firstName ? `, ${firstName}` : ''}.
              </h2>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                {activeCount !== null
                  ? `${activeCount} active setup${activeCount !== 1 ? 's' : ''} across ${pairCount} instruments.`
                  : 'Loading engine state…'}
              </p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
                <span style={{ color: 'var(--bullish)', fontWeight: 600 }}>Engine active</span>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Monitoring 24/7</span>
            </div>
          </div>

          {/* Bottom row: status chips + progress */}
          <div style={{ padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
            {/* Identity chips */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {/* Role */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 99, background: 'var(--accent-bg)', border: '1px solid var(--accent)30' }}>
                {isOwner && <Shield size={12} color="var(--accent-hover)" />}
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-hover)' }}>
                  {isOwner ? 'Owner' : 'Subscriber'}
                </span>
              </div>
              {/* Plan */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 99, background: 'var(--bullish-bg)', border: '1px solid var(--bullish)30' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--bullish)' }}>
                  {planLabel(user?.plan)}
                </span>
              </div>
              {/* Telegram / Alerts */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 99, background: tgLinked ? 'var(--bullish-bg)' : 'var(--card-hover)', border: `1px solid ${tgLinked ? 'var(--bullish)30' : 'var(--border)'}` }}>
                {tgLinked
                  ? <Wifi size={12} color="var(--bullish)" />
                  : <WifiOff size={12} color="var(--text-muted)" />}
                <span style={{ fontSize: 12, fontWeight: 600, color: tgLinked ? 'var(--bullish)' : 'var(--text-muted)' }}>
                  {tgLinked ? 'Telegram linked' : 'Telegram not linked'}
                </span>
              </div>
              {/* Member since */}
              {(() => {
                const since = isOwner ? profile?.member_since : user?.created_at
                return since ? (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Since {fmtMemberSince(since)}
                  </span>
                ) : null
              })()}
            </div>

            {/* Progress tracker */}
            <div className="topbar-progress" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {steps.map((s, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  {i > 0 && <div style={{ width: 16, height: 1, background: 'var(--border)' }} />}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} title={s.label}>
                    {s.done
                      ? <CheckCircle2 size={14} color="var(--bullish)" />
                      : <Circle size={14} color="var(--text-muted)" />}
                    <span style={{ fontSize: 11, color: s.done ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: s.done ? 500 : 400 }}>
                      {s.label}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          <StatCard label="Instruments" value={pairCount ?? '—'} icon={BarChart2} iconColor="var(--info)" sub="Under surveillance" />
          <StatCard label="Active Breakouts" value={activeCount ?? '—'} icon={Activity} iconColor="var(--accent)" sub="Live bias setups" />
          <StatCard label="Retests In Progress" value={retestCount ?? '—'} icon={Zap} iconColor="var(--warning)" sub="Awaiting H4 confirm" />
          <StatCard label="Alerts Fired" value={stats?.total_alerts ?? '—'} icon={Bell} iconColor="var(--bullish)" sub={stats ? `${stats.alerts_today} today` : undefined} />
        </div>

        <LiveChartBoard />

          {/* Latest alerts */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Latest Notifications</h3>
              <Link href="/alerts" style={{ fontSize: 12, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)' }}>
              <AlertTypeFilter types={alertTypes} onChange={setAlertTypes} compact />
            </div>
            {alerts && alerts.items.length === 0 && alertTypes.length > 0 ? (
              <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                No notifications of the types you picked yet.
              </div>
            ) : !alerts || alerts.items.length === 0 ? (
              <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                No alerts fired yet.<br />
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Alerts fire when all 4 conditions are confirmed.</span>
              </div>
            ) : (
              <div>
                {alerts.items.map(a => (
                  <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 20px', borderBottom: '1px solid var(--border)' }}>
                    <div style={{
                      width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                      background: a.direction === 'BULLISH' ? 'var(--bullish-bg)' : 'var(--bearish-bg)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {a.direction === 'BULLISH'
                        ? <TrendingUp size={14} color="var(--bullish)" />
                        : <TrendingDown size={14} color="var(--bearish)" />}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{a.instrument}</span>
                        <span style={{ fontSize: 11, color: a.direction === 'BULLISH' ? 'var(--bullish)' : 'var(--bearish)', fontWeight: 500 }}>
                          {a.direction === 'BULLISH' ? 'Buy' : 'Sell'}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>· {a.h4_classification}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {fmtDate(a.fired_at)}
                        {a.alert_type && a.alert_type !== 'origin' && (
                          <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--warning)', fontWeight: 600 }}>
                            · {typeLabel(a.alert_type)}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="badge badge-delivered" style={{ fontSize: 10, flexShrink: 0 }}>Delivered</span>
                  </div>
                ))}
              </div>
            )}
          </div>

        {/* Personalise */}
        <div style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '20px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <p style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>Personalise</p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Choose your interface accent colour</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {PALETTE.map(swatch => (
              <button
                key={swatch.id}
                title={swatch.name}
                onClick={() => setAccent(swatch.id)}
                style={{
                  width: 28, height: 28,
                  borderRadius: '50%',
                  background: swatch.color,
                  border: accent === swatch.id
                    ? `3px solid var(--text-primary)`
                    : '3px solid transparent',
                  outline: accent === swatch.id ? `2px solid ${swatch.color}` : 'none',
                  outlineOffset: 1,
                  cursor: 'pointer',
                  transition: 'transform 0.15s, border 0.15s',
                  transform: accent === swatch.id ? 'scale(1.15)' : 'scale(1)',
                  flexShrink: 0,
                }}
              />
            ))}
          </div>
        </div>

      </main>
    </>
  )
}
