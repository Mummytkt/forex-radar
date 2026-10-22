'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Radio } from 'lucide-react'
import { LEGAL } from '@/lib/legal'

const DOCS = [
  { href: '/terms', label: 'Terms of Service' },
  { href: '/privacy', label: 'Privacy Policy' },
  { href: '/refunds', label: 'Refunds & Cancellation' },
  { href: '/risk', label: 'Risk Disclaimer' },
]

/** Shared layout for the public legal pages. */
export default function LegalPage({ title, intro, children }: {
  title: string
  intro?: string
  children: React.ReactNode
}) {
  const path = usePathname()
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)' }}>
      <header style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div style={{ maxWidth: 820, margin: '0 auto', padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
            <span style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              <Radio size={15} color="white" />
            </span>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{LEGAL.business}</span>
          </Link>
          <Link href="/login" style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', textDecoration: 'none' }}>Log in</Link>
        </div>
      </header>

      <main style={{ maxWidth: 820, margin: '0 auto', padding: '28px 20px 56px' }}>
        <nav aria-label="Legal documents" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 26 }}>
          {DOCS.map(d => {
            const on = path === d.href
            return (
              <Link key={d.href} href={d.href} style={{
                fontSize: 12, fontWeight: 600, padding: '6px 12px', borderRadius: 999, textDecoration: 'none',
                border: '1px solid', borderColor: on ? 'var(--accent)' : 'var(--border)',
                background: on ? 'var(--accent)' : 'var(--card)', color: on ? 'white' : 'var(--text-secondary)',
              }}>{d.label}</Link>
            )
          })}
        </nav>

        <h1 style={{ fontSize: 'clamp(24px, 4vw, 30px)', fontWeight: 800, letterSpacing: '-0.01em', textWrap: 'balance' }}>{title}</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>Last updated {LEGAL.updated}</p>
        {intro && <p style={{ fontSize: 15, color: 'var(--text-secondary)', marginTop: 16, lineHeight: 1.75, maxWidth: '68ch' }}>{intro}</p>}

        <div className="legal-body" style={{ marginTop: 22 }}>{children}</div>

        <div style={{ marginTop: 40, paddingTop: 18, borderTop: '1px solid var(--border)', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          Questions about this page? Email <a href={`mailto:${LEGAL.email}`} style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>{LEGAL.email}</a>.
        </div>
      </main>
    </div>
  )
}

export function H2({ children }: { children: React.ReactNode }) {
  return <h2 style={{ fontSize: 17, fontWeight: 700, marginTop: 28, marginBottom: 8, color: 'var(--text-primary)' }}>{children}</h2>
}

export function P({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--text-secondary)', marginBottom: 10, maxWidth: '72ch' }}>{children}</p>
}

export function UL({ items }: { items: React.ReactNode[] }) {
  return (
    <ul style={{ paddingLeft: 20, margin: '4px 0 12px', maxWidth: '72ch' }}>
      {items.map((it, i) => (
        <li key={i} style={{ fontSize: 14, lineHeight: 1.8, color: 'var(--text-secondary)', marginBottom: 4 }}>{it}</li>
      ))}
    </ul>
  )
}
