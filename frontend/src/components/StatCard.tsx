import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: number | string
  icon: LucideIcon
  iconColor?: string
  sub?: string
  trend?: string
}

export default function StatCard({ label, value, icon: Icon, iconColor = 'var(--accent)', sub, trend }: Props) {
  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      padding: '18px 20px',
      display: 'flex', flexDirection: 'column', gap: 12,
      boxShadow: 'var(--shadow)',
      transition: 'background 0.15s, border-color 0.15s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: `color-mix(in srgb, ${iconColor} 15%, transparent)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={16} color={iconColor} />
        </div>
      </div>
      <div>
        <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>{value}</div>
        {sub && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 5 }}>{sub}</div>}
        {trend && <div style={{ fontSize: 11, color: 'var(--bullish)', marginTop: 4, fontWeight: 500 }}>{trend}</div>}
      </div>
    </div>
  )
}
