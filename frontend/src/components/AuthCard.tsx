'use client'
import { Radio } from 'lucide-react'

/** Shared centred card layout for the sign-in family of pages (forgot, reset, claim). */
export default function AuthCard({ title, subtitle, children, footer }: {
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 26 }}>
          <div style={{ width: 48, height: 48, borderRadius: 13, background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', boxShadow: '0 0 24px rgba(99,102,241,0.4)' }}>
            <Radio size={22} color="white" />
          </div>
          <h1 style={{ fontSize: 19, fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h1>
          {subtitle && <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6 }}>{subtitle}</p>}
        </div>
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: 26, boxShadow: 'var(--shadow)' }}>
          {children}
        </div>
        {footer && <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 18, lineHeight: 1.8 }}>{footer}</div>}
      </div>
    </div>
  )
}

export const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 14, background: 'var(--bg)',
  border: '1px solid var(--border)', color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
}

export const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6,
}

export const buttonStyle = (disabled: boolean): React.CSSProperties => ({
  width: '100%', padding: '11px', borderRadius: 9, fontSize: 14, fontWeight: 700, background: 'var(--accent)',
  color: 'white', border: 'none', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.6 : 1,
  boxShadow: '0 2px 10px rgba(99,102,241,0.35)',
})

export const linkStyle: React.CSSProperties = { color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }
