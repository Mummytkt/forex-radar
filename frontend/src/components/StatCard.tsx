import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: number | string
  icon: LucideIcon
  accent?: string
  sub?: string
}

export default function StatCard({ label, value, icon: Icon, accent = 'var(--accent)', sub }: Props) {
  return (
    <div className="rounded-xl p-5 flex items-start justify-between"
      style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <div>
        <p className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{label}</p>
        <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{value}</p>
        {sub && <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
      </div>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${accent}22` }}>
        <Icon size={18} style={{ color: accent }} />
      </div>
    </div>
  )
}
