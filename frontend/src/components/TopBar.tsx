'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Radio, LayoutGrid, ChevronDown, UserCircle2, Sun, Moon, LogOut, Activity } from 'lucide-react'
import { isForexOpen } from '@/lib/utils'
import { useTimezone, getAbbrStr } from '@/lib/timezone'
import useSWR from 'swr'
import { useAuth } from '@/lib/auth'
import { useTheme } from '@/lib/theme'
import { API_BASE } from '@/lib/api'
import { HUB_HREF, visibleNav } from '@/lib/nav'
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

const menuPanel: React.CSSProperties = {
  position: 'absolute', top: 'calc(100% + 8px)', right: 0, zIndex: 40,
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
  boxShadow: '0 12px 32px rgba(0,0,0,0.35)', padding: 8,
}

const pillBtn: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, height: 34, padding: '0 11px',
  borderRadius: 9, border: '1px solid var(--border)', background: 'var(--card)',
  color: 'var(--text-primary)', cursor: 'pointer', fontSize: 12.5, fontWeight: 600,
  position: 'relative',
}

export default function TopBar({ title, subtitle }: Props) {
  const [timeStr, setTimeStr] = useState('')
  const [forexOpen, setForexOpen] = useState(false)
  const [menu, setMenu] = useState<'jump' | 'account' | null>(null)
  const { timezone } = useTimezone()
  const { user, authEnabled, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const path = usePathname()
  const isOwner = user?.role === 'OWNER'
  const { data: unreadData } = useSWR<{ unread: number } | null>(
    user && !isOwner ? UNREAD_KEY : null, quietFetch, { refreshInterval: 60000 })
  const unread = unreadData?.unread ?? 0

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

  useEffect(() => { setMenu(null) }, [path])

  const groups = visibleNav(isOwner)

  return (
    <header style={{
      display: 'flex', alignItems: 'center', gap: 14,
      padding: '12px 20px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface)',
      position: 'sticky', top: 0, zIndex: 20,
      transition: 'background 0.25s, border-color 0.25s',
    }}>
      {menu && <div onClick={() => setMenu(null)} style={{ position: 'fixed', inset: 0, zIndex: 30 }} />}

      {/* Brand — always takes you back to the hub */}
      <Link href={HUB_HREF} title="Home" style={{ display: 'flex', alignItems: 'center', gap: 9, textDecoration: 'none', flexShrink: 0 }}>
        <span style={{
          width: 32, height: 32, borderRadius: 9, background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 12px rgba(99,102,241,0.4)',
        }}>
          <Radio size={15} color="white" />
        </span>
        <span className="desktop-only" style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
          <span style={{ fontWeight: 700, fontSize: 12.5, color: 'var(--text-primary)' }}>MummyTKT&apos;s</span>
          <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--accent)' }}>Bias Pointer</span>
        </span>
      </Link>

      <span className="desktop-only" style={{ width: 1, height: 28, background: 'var(--border)', flexShrink: 0 }} />

      <div style={{ minWidth: 0, flex: 1 }}>
        <h1 style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', lineHeight: 1.2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</h1>
        {subtitle && <p className="desktop-only" style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{subtitle}</p>}
      </div>

      {/* Desktop: market status + clock */}
      <div className="topbar-clock-full" style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className={forexOpen ? 'pulse' : ''} style={{ width: 7, height: 7, borderRadius: '50%', background: forexOpen ? 'var(--bullish)' : 'var(--bearish)', display: 'inline-block' }} />
          <span style={{ color: 'var(--text-secondary)' }}>Forex {forexOpen ? 'Open' : 'Closed'}</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
          <span style={{ color: 'var(--text-secondary)' }}>Crypto Open</span>
        </span>
        <span style={{
          fontFamily: 'monospace', padding: '4px 10px', borderRadius: 6,
          background: 'var(--card)', color: 'var(--text-secondary)', border: '1px solid var(--border)',
        }}>{timeStr}</span>
      </div>

      {/* Jump to */}
      <div style={{ position: 'relative', zIndex: 35 }}>
        <button onClick={() => setMenu(menu === 'jump' ? null : 'jump')} style={pillBtn} aria-label={unread > 0 ? 'Jump to (new updates)' : 'Jump to'}>
          <LayoutGrid size={14} />
          <span className="desktop-only">Jump to</span>
          <ChevronDown size={13} className="desktop-only" />
          {unread > 0 && <span style={{ position: 'absolute', top: -3, right: -3, width: 9, height: 9, borderRadius: '50%', background: 'var(--bearish)', boxShadow: '0 0 0 2px var(--surface)' }} />}
        </button>
        {menu === 'jump' && (
          <div style={{ ...menuPanel, width: 'min(560px, calc(100vw - 32px))', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 4 }}>
            <Link href={HUB_HREF} style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 8, padding: '9px 10px', borderRadius: 8, textDecoration: 'none', color: 'var(--accent-hover)', fontSize: 13, fontWeight: 600, background: 'var(--accent-bg)' }}>
              <LayoutGrid size={14} /> All pages (home)
            </Link>
            {groups.map(g => (
              <div key={g.label} style={{ display: 'flex', flexDirection: 'column', gap: 1, padding: '4px 0' }}>
                <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', padding: '4px 10px' }}>{g.label}</div>
                {g.items.map(({ href, icon: Icon, label, color }) => {
                  const active = href === '/dashboard' ? path === '/dashboard' : path.startsWith(href)
                  return (
                    <Link key={href} href={href} style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 8,
                      textDecoration: 'none', fontSize: 13, fontWeight: active ? 600 : 400,
                      color: active ? 'var(--accent-hover)' : 'var(--text-secondary)',
                      background: active ? 'var(--accent-bg)' : 'transparent',
                    }}>
                      <Icon size={14} color={color} /> {label}
                      {href === '/strategy' && unread > 0 && (
                        <span style={{ marginLeft: 'auto', minWidth: 18, height: 18, padding: '0 5px', borderRadius: 999, background: 'var(--bearish)', color: 'white', fontSize: 10.5, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                          {unread > 9 ? '9+' : unread}
                        </span>
                      )}
                    </Link>
                  )
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Account menu */}
      <div style={{ position: 'relative', zIndex: 35 }}>
        <button onClick={() => setMenu(menu === 'account' ? null : 'account')} style={{ ...pillBtn, padding: '0 8px' }} aria-label="Account menu">
          <UserCircle2 size={17} />
        </button>
        {menu === 'account' && (
          <div style={{ ...menuPanel, width: 230, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {authEnabled && user && (
              <div style={{ padding: '8px 10px', borderRadius: 9, background: 'var(--card)', border: '1px solid var(--border)' }}>
                <p style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.name || user.email.split('@')[0]}
                </p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{isOwner ? 'Owner · Lifetime' : user.plan}</p>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 8, background: 'var(--bullish-bg)' }}>
              <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', display: 'inline-block' }} />
              <span style={{ fontSize: 11.5, color: 'var(--bullish)', fontWeight: 500 }}>Engine active</span>
              <Activity size={11} color="var(--bullish)" style={{ marginLeft: 'auto' }} />
            </div>
            <span className="mobile-only" style={{ alignItems: 'center', gap: 10, padding: '4px 10px', fontSize: 11.5, color: 'var(--text-secondary)' }}>
              <span className={forexOpen ? 'pulse' : ''} style={{ width: 7, height: 7, borderRadius: '50%', background: forexOpen ? 'var(--bullish)' : 'var(--bearish)', display: 'inline-block' }} />
              FX {forexOpen ? 'Open' : 'Closed'} · Crypto Open · {timeStr}
            </span>
            <button onClick={toggle} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--card-hover)', color: 'var(--text-secondary)', fontSize: 12.5 }}>
              {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
            {authEnabled && user && (
              <button onClick={logout} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--bearish)', fontSize: 12.5 }}>
                <LogOut size={13} /> Sign out
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
