'use client'
import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { Activity, Zap, Bell, BarChart2, TrendingUp, TrendingDown, ArrowRight, Shield, CheckCircle2, Circle, Wifi, WifiOff } from 'lucide-react'
import Link from 'next/link'
import TopBar from '@/components/TopBar'
import StatCard from '@/components/StatCard'
import { fetcher } from '@/lib/api'
import { timeAgo } from '@/lib/utils'
import { useTimezone } from '@/lib/timezone'
import { useAuth } from '@/lib/auth'
import type { InstrumentOverview, Stats, AlertsPage } from '@/lib/types'

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
  return plan ?? '—'
}

export default function OverviewPage() {
  const [greeting, setGreeting] = useState('')
  const [today, setToday] = useState('')
  const { fmtDate } = useTimezone()
  const { user } = useAuth()
  const { data: instruments } = useSWR<InstrumentOverview[]>('/api/overview', fetcher, { refreshInterval: 30000 })
  const { data: stats } = useSWR<Stats>('/api/stats', fetcher, { refreshInterval: 30000 })
  const { data: alerts } = useSWR<AlertsPage>('/api/alerts?limit=5', fetcher, { refreshInterval: 30000 })
  const { data: profile } = useSWR<Profile>('/api/profile', fetcher, { refreshInterval: 60000 })

  useEffect(() => {
    const h = new Date().getHours()
    setGreeting(h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening')
    setToday(new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))
  }, [])

  const firstName = user?.name?.split(' ')[0] || user?.name || ''

  const activeSetups = (instruments ?? []).filter(i => i.state !== 'IDLE')
    .sort((a, b) => {
      const o = { RETEST_IN_PROGRESS: 0, BREAKOUT_ACTIVE: 1, IDLE: 2 }
      return o[a.state] - o[b.state]
    })

  const isOwner = user?.role === 'OWNER'
  const steps = [
    { label: 'Engine running', done: true },
    { label: 'Instruments loaded', done: (stats?.total_instruments ?? 0) > 0 },
    { label: isOwner ? 'Telegram linked' : 'Alerts active', done: profile?.telegram_configured ?? false },
    { label: 'First alert fired', done: (profile?.first_alert_at ?? null) !== null },
  ]

  return (
    <>
      <TopBar title="Overview" subtitle={today} />
      <main className="page-padded" style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

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
                {stats
                  ? `${stats.active_breakouts} active setup${stats.active_breakouts !== 1 ? 's' : ''} across ${stats.total_instruments} instruments.`
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 99, background: profile?.telegram_configured ? 'var(--bullish-bg)' : 'var(--card-hover)', border: `1px solid ${profile?.telegram_configured ? 'var(--bullish)30' : 'var(--border)'}` }}>
                {profile?.telegram_configured
                  ? <Wifi size={12} color="var(--bullish)" />
                  : <WifiOff size={12} color="var(--text-muted)" />}
                <span style={{ fontSize: 12, fontWeight: 600, color: profile?.telegram_configured ? 'var(--bullish)' : 'var(--text-muted)' }}>
                  {profile?.telegram_configured
                    ? (isOwner ? 'Telegram linked' : 'Alerts active')
                    : (isOwner ? 'Telegram not set' : 'Alerts not configured')}
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
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
          <StatCard label="Instruments" value={stats?.total_instruments ?? '—'} icon={BarChart2} iconColor="var(--info)" sub="Under surveillance" />
          <StatCard label="Active Breakouts" value={stats?.active_breakouts ?? '—'} icon={Activity} iconColor="var(--accent)" sub="Live bias setups" />
          <StatCard label="Retests In Progress" value={stats?.retests_in_progress ?? '—'} icon={Zap} iconColor="var(--warning)" sub="Awaiting H4 confirm" />
          <StatCard label="Alerts Fired" value={stats?.total_alerts ?? '—'} icon={Bell} iconColor="var(--bullish)" sub={stats ? `${stats.alerts_today} today` : undefined} />
        </div>

        <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

          {/* Active setups */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Active Setups</h3>
              <Link href="/instruments" style={{ fontSize: 12, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                View all <ArrowRight size={12} />
              </Link>
            </div>
            {activeSetups.length === 0 ? (
              <div style={{ padding: '32px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
                No active setups currently.<br />
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Next H4 check fires at the top of each 4h candle.</span>
              </div>
            ) : (
              <div>
                {activeSetups.slice(0, 8).map((inst) => {
                  const setupDir = inst.direction === 'BULLISH' ? '↑' : inst.direction === 'BEARISH' ? '↓' : ''
                  const confirmed = inst.last_alert_direction
                  return (
                    <div key={inst.instrument} style={{
                      display: 'flex', alignItems: 'center', gap: 12,
                      padding: '11px 20px', borderBottom: '1px solid var(--border)',
                    }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{inst.instrument}</span>
                          {confirmed ? (
                            <span style={{
                              display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600,
                              color: confirmed === 'BULLISH' ? 'var(--bullish)' : 'var(--bearish)',
                            }}>
                              {confirmed === 'BULLISH' ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                              {confirmed === 'BULLISH' ? 'Buy confirmed' : 'Sell confirmed'}
                            </span>
                          ) : (
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              {setupDir} Setup forming
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                          {inst.active_sources_count > 0 ? `${inst.active_sources_count} sources` : 'No sources'} · {timeAgo(inst.last_updated)}
                        </div>
                      </div>
                      <span className="badge" style={{
                        background: inst.state === 'RETEST_IN_PROGRESS' ? 'var(--warning-bg)' : 'var(--accent-bg)',
                        color: inst.state === 'RETEST_IN_PROGRESS' ? 'var(--warning)' : 'var(--accent-hover)',
                        fontSize: 10,
                      }}>
                        {inst.state === 'RETEST_IN_PROGRESS' && (
                          <span className="pulse" style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--warning)', display: 'inline-block' }} />
                        )}
                        {inst.state === 'RETEST_IN_PROGRESS' ? `${setupDir} Retesting` : `${setupDir} Setup`}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Latest alerts */}
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>Latest Notifications</h3>
              <Link href="/alerts" style={{ fontSize: 12, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                View all <ArrowRight size={12} />
              </Link>
            </div>
            {!alerts || alerts.items.length === 0 ? (
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
                        {a.alert_classification && a.alert_classification !== 'origin' && (
                          <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--warning)', fontWeight: 600 }}>
                            · continuation
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
        </div>

      </main>
    </>
  )
}
