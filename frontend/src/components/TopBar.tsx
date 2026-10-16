'use client'
import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { isForexOpen } from '@/lib/utils'
import { useTimezone, getAbbrStr } from '@/lib/timezone'
import { useSidebar } from './LayoutShell'
import useSWR from 'swr'
import { useAuth } from '@/lib/auth'
import { API_BASE } from '@/lib/api'
import { UNREAD_KEY } from './UpdatesSection'

const quietFetch = (url: string) => {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return fetch(`${API_BASE}${url}`, { headers: t ? { Authorization: `Bearer ${t}` } : {} })
    .then(r => (r.ok ? r.json() : null)).catch(() => null)
}

interface Props {
  title: string
  subtitle?: string
}

export default function TopBar({ title, subtitle }: Props) {
  const [timeStr, setTimeStr] = useState('')
  const [forexOpen, setForexOpen] = useState(false)
  const { timezone } = useTimezone()
  const { toggle } = useSidebar()
  const { user } = useAuth()
  const { data: unreadData } = useSWR<{ unread: number } | null>(
    user && user.role !== 'OWNER' ? UNREAD_KEY : null, quietFetch, { refreshInterval: 60000 })
  const hasUnread = (unreadData?.unread ?? 0) > 0

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const local = now.toLocaleTimeString('en-GB', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        timeZone: timezone,
      })
      setTimeStr(`${local} ${getAbbrStr(timezone)}`)
      setForexOpen(isForexOpen())
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [timezone])

  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 24px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface)',
      position: 'sticky', top: 0, zIndex: 20,
      transition: 'background 0.25s, border-color 0.25s',
    }}>
      <button
        onClick={toggle}
        className="mobile-only"
        style={{
          width: 34, height: 34, borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--card)',
          color: 'var(--text-primary)',
          cursor: 'pointer',
          alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, position: 'relative',
        }}
        aria-label={hasUnread ? 'Menu (new updates)' : 'Menu'}
      >
        <Menu size={16} />
        {hasUnread && <span style={{ position: 'absolute', top: 5, right: 5, width: 8, height: 8, borderRadius: '50%', background: 'var(--bearish)', boxShadow: '0 0 0 2px var(--card)' }} />}
      </button>
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', lineHeight: 1.2 }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {/* Desktop: full clock + market labels */}
      <div className="topbar-clock-full" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className={forexOpen ? 'pulse' : ''} style={{ width: 7, height: 7, borderRadius: '50%', background: forexOpen ? 'var(--bullish)' : 'var(--bearish)', display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>Forex {forexOpen ? 'Open' : 'Closed'}</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>Crypto Open</span>
          </span>
        </div>
        <span style={{
          fontSize: 12, fontFamily: 'monospace',
          padding: '4px 10px', borderRadius: 6,
          background: 'var(--card)', color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}>{timeStr}</span>
      </div>

      {/* Mobile: compact dots only */}
      <div className="market-dots-mobile" style={{ alignItems: 'center', gap: 10 }}>
        <span title={`Forex ${forexOpen ? 'Open' : 'Closed'}`} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
          <span className={forexOpen ? 'pulse' : ''} style={{ width: 7, height: 7, borderRadius: '50%', background: forexOpen ? 'var(--bullish)' : 'var(--bearish)', display: 'inline-block', flexShrink: 0 }} />
          FX {forexOpen ? 'Open' : 'Closed'}
        </span>
        <span title="Crypto Open" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)' }}>
          <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block', flexShrink: 0 }} />
          Crypto
        </span>
      </div>
    </header>
  )
}
