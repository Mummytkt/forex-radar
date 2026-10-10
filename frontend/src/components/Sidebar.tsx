'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Bell, BarChart2, BookOpen, Settings, Radio } from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/alerts', icon: Bell, label: 'Alerts' },
  { href: '/instruments', icon: BarChart2, label: 'Instruments' },
  { href: '/strategy', icon: BookOpen, label: 'Strategy' },
  { href: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="fixed inset-y-0 left-0 w-56 flex flex-col z-20"
      style={{ background: 'var(--surface)', borderRight: '1px solid var(--border)' }}>
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: 'var(--accent)' }}>
          <Radio size={16} className="text-white" />
        </div>
        <div>
          <div className="font-bold text-sm leading-tight" style={{ color: 'var(--text-primary)' }}>Bias Radar</div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Pro Engine</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ href, icon: Icon, label }) => {
          const active = path === href
          return (
            <Link key={href} href={href}
              className={clsx('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                active
                  ? 'text-white'
                  : 'hover:text-white'
              )}
              style={active
                ? { background: 'var(--accent)', color: 'white' }
                : { color: 'var(--text-secondary)' }
              }>
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t text-xs" style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
        Phase 1 · Engine v1.0
      </div>
    </aside>
  )
}
