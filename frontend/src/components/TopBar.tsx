'use client'
import { useState, useEffect } from 'react'
import { isForexOpen } from '@/lib/utils'
import { useTimezone, getAbbrStr } from '@/lib/timezone'

interface Props {
  title: string
  subtitle?: string
}

export default function TopBar({ title, subtitle }: Props) {
  const [timeStr, setTimeStr] = useState('')
  const [forexOpen, setForexOpen] = useState(false)
  const { timezone } = useTimezone()

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
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', lineHeight: 1.2 }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{subtitle}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
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
    </header>
  )
}
