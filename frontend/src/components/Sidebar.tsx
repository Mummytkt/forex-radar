'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Bell, BarChart2, BookOpen, Settings,
  Radio, SlidersHorizontal, Moon, Sun, Activity, LogOut, UserCircle2, X, BookMarked, Target
} from 'lucide-react'
import { useTheme } from '@/lib/theme'
import { useAuth } from '@/lib/auth'
import { useSidebar } from './LayoutShell'

const SECTIONS = [
  {
    label: 'Workspace',
    links: [
      { href: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
      { href: '/strategy', icon: BookOpen, label: 'Strategy' },
      { href: '/journal', icon: BookMarked, label: 'Journal' },
    ],
  },
  {
    label: 'Monitoring',
    links: [
      { href: '/instruments', icon: BarChart2, label: 'Instruments' },
    ],
  },
  {
    label: 'Delivery',
    links: [
      { href: '/alerts', icon: Bell, label: 'History' },
      { href: '/price-alerts', icon: Target, label: 'Price Alerts' },
      { href: '/preferences', icon: SlidersHorizontal, label: 'Preferences' },
    ],
  },
  {
    label: 'Account',
    links: [
      { href: '/account', icon: UserCircle2, label: 'Account' },
      { href: '/settings', icon: Settings, label: 'Settings' },
    ],
  },
]

export default function Sidebar() {
  const path = usePathname()
  const { theme, toggle } = useTheme()
  const { user, authEnabled, logout } = useAuth()
  const { open, close } = useSidebar()

  return (
    <aside
      className={`sidebar-mobile${open ? ' sidebar-open' : ''}`}
      style={{
        position: 'fixed', top: 0, left: 0, bottom: 0,
        width: 220,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        zIndex: 30,
        transition: 'background 0.25s, border-color 0.25s',
      }}
    >
      {/* Logo */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '20px 18px 18px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
          boxShadow: '0 0 12px rgba(99,102,241,0.4)',
        }}>
          <Radio size={16} color="white" />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.2 }}>
            MummyTKT's
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginTop: 1 }}>
            Bias Pointer
          </div>
        </div>
        <button
          onClick={close}
          className="mobile-only"
          style={{
            marginLeft: 'auto', width: 28, height: 28, borderRadius: 7,
            border: '1px solid var(--border)', background: 'var(--card-hover)',
            color: 'var(--text-secondary)', cursor: 'pointer',
            alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}
        >
          <X size={14} />
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '12px 10px', overflowY: 'auto' }}>
        {SECTIONS.map((section) => (
          <div key={section.label} style={{ marginBottom: 4 }}>
            <div style={{
              fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '0.08em', color: 'var(--text-muted)',
              padding: '10px 10px 5px',
            }}>
              {section.label}
            </div>
            {section.links.map(({ href, icon: Icon, label }) => {
              const active = href === '/dashboard' ? path === '/dashboard' : path.startsWith(href)
              return (
                <Link key={href} href={href} onClick={close}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 9,
                    padding: '8px 10px', borderRadius: 8,
                    fontSize: 13, fontWeight: active ? 600 : 400,
                    color: active ? 'white' : 'var(--text-secondary)',
                    background: active ? 'var(--accent)' : 'transparent',
                    textDecoration: 'none',
                    marginBottom: 1,
                    transition: 'all 0.12s',
                    boxShadow: active ? '0 2px 8px rgba(99,102,241,0.35)' : 'none',
                  }}
                  onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = 'var(--card-hover)'; (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)' } }}
                  onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)' } }}
                >
                  <Icon size={15} />
                  {label}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div style={{
        padding: '10px 14px 12px',
        borderTop: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        {/* User info (when logged in) */}
        {authEnabled && user && (
          <div style={{ padding: '8px 10px', borderRadius: 9, background: 'var(--card)', border: '1px solid var(--border)', marginBottom: 2 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
                <div style={{ width: 26, height: 26, borderRadius: '50%', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <UserCircle2 size={14} color="var(--accent-hover)" />
                </div>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.name || user.email.split('@')[0]}
                  </p>
                  <p style={{ fontSize: 10, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.role === 'OWNER' ? 'Owner · Lifetime' : user.plan}
                  </p>
                </div>
              </div>
              <button onClick={logout} title="Sign out"
                style={{ width: 26, height: 26, borderRadius: 6, border: 'none', cursor: 'pointer', background: 'var(--card-hover)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <LogOut size={12} />
              </button>
            </div>
          </div>
        )}

        {/* Engine status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderRadius: 8, background: 'var(--bullish-bg)' }}>
          <span className="pulse" style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--bullish)', flexShrink: 0, display: 'inline-block' }} />
          <span style={{ fontSize: 11, color: 'var(--bullish)', fontWeight: 500 }}>Engine active</span>
          <Activity size={11} color="var(--bullish)" style={{ marginLeft: 'auto' }} />
        </div>

        {/* Theme toggle */}
        <button onClick={toggle} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '7px 8px', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: 'var(--card-hover)', color: 'var(--text-secondary)',
          fontSize: 12, width: '100%', transition: 'background 0.15s',
        }}>
          {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  )
}
