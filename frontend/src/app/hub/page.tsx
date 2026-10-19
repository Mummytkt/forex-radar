'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import { ArrowUpRight } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { fetcher } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { timeAgo } from '@/lib/utils'
import { visibleNav, type NavItem } from '@/lib/nav'
import { UNREAD_KEY } from '@/components/UpdatesSection'
import type { Stats, AlertsPage, PriceAlertsList } from '@/lib/types'

function greeting(): string {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

function Card({ item, group, detail, badge, featured }: { item: NavItem; group: string; detail?: string | null; badge?: number; featured?: boolean }) {
  const Icon = item.icon
  return (
    <Link href={item.href} className={`hub-card${featured ? ' hub-featured' : ''}`} style={{
      ['--c' as string]: item.color,
      gridColumn: featured ? 'span 2' : undefined,
      display: 'flex', flexDirection: 'column', gap: 12, padding: featured ? '24px 24px 22px' : '20px 18px 18px',
      borderRadius: 18, textDecoration: 'none', position: 'relative',
      minHeight: featured ? 156 : 140,
    } as React.CSSProperties}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="hub-icon" style={{
          width: featured ? 46 : 40, height: featured ? 46 : 40, borderRadius: 13,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={featured ? 21 : 18} color="#fff" />
        </span>
        {badge ? (
          <span style={{ minWidth: 20, height: 20, padding: '0 6px', borderRadius: 999, background: 'var(--bearish)', color: 'white', fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            {badge > 9 ? '9+' : badge}
          </span>
        ) : (
          <ArrowUpRight size={17} className="hub-arrow" />
        )}
      </div>
      <div>
        <div className="hub-group" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>{group}</div>
        <div className="hub-title" style={{ fontWeight: 800, fontSize: featured ? 19 : 15.5, letterSpacing: '-0.01em' }}>{item.label}</div>
        <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 5, lineHeight: 1.55 }}>{item.desc}</div>
      </div>
      {detail && (
        <div className="hub-detail" style={{ marginTop: 'auto', fontSize: 11.5, fontWeight: 700 }}>{detail}</div>
      )}
    </Link>
  )
}

export default function HubPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const { data: stats } = useSWR<Stats>('/api/stats', fetcher, { refreshInterval: 60000 })
  const { data: alerts } = useSWR<AlertsPage>('/api/alerts?limit=1', fetcher, { refreshInterval: 60000 })
  const { data: levels } = useSWR<PriceAlertsList>('/api/price-alerts?tab=active', fetcher, { refreshInterval: 60000 })
  const { data: unreadData } = useSWR<{ unread: number }>(user && !isOwner ? UNREAD_KEY : null, fetcher, { refreshInterval: 60000 })
  const unread = unreadData?.unread ?? 0

  const lastAlert = alerts?.items?.[0]
  const details: Record<string, string | null> = {
    '/dashboard': stats ? `${stats.active_breakouts} active setup${stats.active_breakouts === 1 ? '' : 's'} · ${stats.retests_in_progress} reacting now` : null,
    '/alerts': lastAlert ? `Last signal ${timeAgo(lastAlert.fired_at)} · ${lastAlert.instrument}` : alerts ? 'No signals yet' : null,
    '/price-alerts': levels ? `${levels.items.length} level${levels.items.length === 1 ? '' : 's'} watched` : null,
    '/instruments': stats ? `${stats.total_instruments} pairs` : null,
    '/strategy': unread > 0 ? `${unread} new update${unread === 1 ? '' : 's'}` : null,
  }

  const name = user?.name || user?.email?.split('@')[0] || ''
  const [hello, setHello] = useState('Welcome back')
  useEffect(() => { setHello(greeting()) }, [])

  return (
    <>
      <TopBar title="Home" subtitle="Everything in one place" />
      <div style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
        {/* Soft background glows, like the landing page */}
        <div className="hub-glow lp-drift" style={{ left: '-8%', top: '-10%', width: '42%', height: '50%', background: 'radial-gradient(circle, rgba(99,102,241,0.22), transparent 70%)' }} />
        <div className="hub-glow lp-drift" style={{ right: '-10%', top: '20%', width: '40%', height: '55%', background: 'radial-gradient(circle, rgba(236,72,153,0.12), rgba(245,158,11,0.08) 45%, transparent 72%)' }} />
        <div className="hub-glow lp-drift" style={{ left: '25%', bottom: '-15%', width: '45%', height: '45%', background: 'radial-gradient(circle, rgba(16,185,129,0.10), transparent 70%)' }} />
      <main className="page-padded" style={{ position: 'relative', zIndex: 1, padding: '30px 28px 44px', display: 'flex', flexDirection: 'column', gap: 26, maxWidth: 1180, width: '100%', margin: '0 auto' }}>
        <div>
          <h2 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            {hello}, <span className="lp-grad1">{name || 'trader'}</span>
          </h2>
          <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginTop: 6 }}>
            Where would you like to go? <span className="lp-grad2" style={{ fontWeight: 600 }}>Know the direction. Trade with confidence.</span>
          </p>
        </div>

        <div className="hub-grid">
          {visibleNav(isOwner).flatMap(group => group.items.map(item => (
            <Card
              key={item.href}
              item={item}
              group={group.label}
              detail={details[item.href]}
              badge={item.href === '/strategy' ? unread : undefined}
              featured={item.href === '/dashboard'}
            />
          )))}
        </div>
      </main>
      </div>
    </>
  )
}
