'use client'
import { useState, useEffect } from 'react'
import { isForexOpen } from '@/lib/utils'

export default function TopBar({ title }: { title: string }) {
  const [utc, setUtc] = useState('')
  const [forexOpen, setForexOpen] = useState(false)

  useEffect(() => {
    const tick = () => {
      setUtc(new Date().toUTCString().slice(17, 25) + ' UTC')
      setForexOpen(isForexOpen())
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b"
      style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
      <h1 className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>{title}</h1>
      <div className="flex items-center gap-4">
        {/* Market status */}
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${forexOpen ? 'bg-green-400 pulse' : 'bg-red-500'}`} />
            <span style={{ color: 'var(--text-secondary)' }}>Forex {forexOpen ? 'Open' : 'Closed'}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 pulse" />
            <span style={{ color: 'var(--text-secondary)' }}>Crypto Open</span>
          </span>
        </div>
        <span className="text-xs font-mono px-2 py-1 rounded"
          style={{ background: 'var(--card)', color: 'var(--text-secondary)' }}>{utc}</span>
      </div>
    </header>
  )
}
