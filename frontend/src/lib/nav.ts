import {
  Compass, BookOpen, BookMarked, FlaskConical, BarChart2, ScrollText, Crosshair,
  SlidersHorizontal, Gift, Briefcase, UserCircle2, Settings, type LucideIcon,
} from 'lucide-react'

// One list drives the home hub cards and the top bar's "Jump to" menu.
export interface NavItem {
  href: string
  icon: LucideIcon
  label: string
  desc: string
  color: string          // card tint, glow and title colour
  ownerOnly?: boolean
  ownerLabel?: string   // owners see the Strategy page under another name
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export const HUB_HREF = '/hub'

export const NAV: NavGroup[] = [
  {
    label: 'Trade Desk',
    items: [
      { href: '/dashboard', color: '#6366f1', icon: Compass, label: 'Bias Board', desc: 'Live setups, the chart board and your latest signals' },
      { href: '/strategy', color: '#a855f7', icon: BookOpen, label: 'Playbook', ownerLabel: 'Strategy', desc: 'How the Bias Pointer reads the market, plus updates' },
      { href: '/journal', color: '#f59e0b', icon: BookMarked, label: 'Journal', desc: 'Log and review your own trades' },
      { href: '/backtest', color: '#14b8a6', icon: FlaskConical, label: 'Backtest', desc: 'Record and test setups on past charts' },
    ],
  },
  {
    label: 'Markets',
    items: [
      { href: '/instruments', color: '#38bdf8', icon: BarChart2, label: 'Markets', desc: 'Every pair the Bias Pointer watches' },
    ],
  },
  {
    label: 'Signals',
    items: [
      { href: '/alerts', color: '#22c55e', icon: ScrollText, label: 'Signal Log', desc: 'Every alert sent to your Telegram' },
      { href: '/price-alerts', color: '#f97316', icon: Crosshair, label: 'Level Watch', desc: 'Get pinged when price reaches your level' },
      { href: '/preferences', color: '#ec4899', icon: SlidersHorizontal, label: 'Alert Filters', desc: 'Choose which confirmation types reach your Telegram' },
    ],
  },
  {
    label: 'Rewards',
    items: [
      { href: '/affiliate', color: '#eab308', icon: Gift, label: 'Refer & Earn', desc: 'Earn a share of every subscriber you bring in' },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/business', color: '#10b981', icon: Briefcase, label: 'Business', desc: 'Revenue, subscribers and platform health', ownerOnly: true },
      { href: '/account', color: '#818cf8', icon: UserCircle2, label: 'Account', desc: 'Your sign-in details, plan and billing' },
      { href: '/settings', color: '#64748b', icon: Settings, label: 'Settings', desc: 'Your pairs, profile and Telegram link' },
    ],
  },
]

export function visibleNav(isOwner: boolean): NavGroup[] {
  return NAV.map(g => ({
    ...g,
    items: g.items
      .filter(i => !i.ownerOnly || isOwner)
      .map(i => (isOwner && i.ownerLabel ? { ...i, label: i.ownerLabel } : i)),
  })).filter(g => g.items.length > 0)
}
