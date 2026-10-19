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
    <Link href={item.href} className="hub-card" style={{
      gridColumn: featured ? 'span 2' : undefined,
      display: 'flex', flexDirection: 'column', gap: 12, padding: featured ? '22px 22px 20px' : '18px 18px 16px',
      borderRadius: 14, textDecoration: 'none', position: 'relative',
      background: featured ? 'linear-gradient(135deg, var(--accent-bg), var(--card))' : 'var(--card)',
      border: `1px solid ${featured ? 'var(--accent)' : 'var(--border)'}`,
      minHeight: featured ? 150 : 132,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          width: featured ? 42 : 36, height: featured ? 42 : 36, borderRadius: 11,
          background: featured ? 'var(--accent)' : 'var(--accent-bg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={featured ? 20 : 17} color={featured ? 'white' : 'var(--accent-hover)'} />
        </span>
        {badge ? (
          <span style={{ minWidth: 20, height: 20, padding: '0 6px', borderRadius: 999, background: 'var(--bearish)', color: 'white', fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            {badge > 9 ? '9+' : badge}
          </span>
        ) : (
          <ArrowUpRight size={16} color="var(--text-muted)" className="hub-arrow" />
        )}
      </div>
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 3 }}>{group}</div>
        <div style={{ fontWeight: 700, fontSize: featured ? 18 : 15, color: 'var(--text-primary)' }}>{item.label}</div>
        <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>{item.desc}</div>
      </div>
      {detail && (
        <div style={{ marginTop: 'auto', fontSize: 11.5, fontWeight: 600, color: 'var(--accent-hover)' }}>{detail}</div>
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
      <main className="page-padded" style={{ flex: 1, padding: '28px 28px 40px', display: 'flex', flexDirection: 'column', gap: 26, maxWidth: 1180, width: '100%', margin: '0 auto' }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            {hello}{name ? `, ${name}` : ''}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Where would you like to go?</p>
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
    </>
  )
}
