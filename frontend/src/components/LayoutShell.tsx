'use client'
import { usePathname } from 'next/navigation'
import { ThemeProvider } from '@/lib/theme'
import { AuthProvider } from '@/lib/auth'
import { TimezoneProvider } from '@/lib/timezone'
import { AccentProvider } from '@/lib/useAccent'

const FULL_PAGE_PATHS = ['/login', '/join', '/', '/signup', '/forgot', '/reset', '/claim',
  '/terms', '/privacy', '/refunds', '/risk']

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const isFullPage = FULL_PAGE_PATHS.some(p => path === p || path.startsWith(p + '?'))

  return (
    <ThemeProvider>
      <AccentProvider>
      <TimezoneProvider>
        <AuthProvider>
          {isFullPage ? (
            children
          ) : (
            // No side menu: pages are reached from the home hub (/hub) and the
            // top bar's "Jump to" menu.
            <div style={{
              display: 'flex', flexDirection: 'column', minHeight: '100vh',
              background: 'var(--bg)',
            }}>
              {children}
            </div>
          )}
        </AuthProvider>
      </TimezoneProvider>
      </AccentProvider>
    </ThemeProvider>
  )
}
