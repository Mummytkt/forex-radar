'use client'
import { usePathname } from 'next/navigation'
import { ThemeProvider } from '@/lib/theme'
import { AuthProvider } from '@/lib/auth'
import { TimezoneProvider } from '@/lib/timezone'
import Sidebar from './Sidebar'

const FULL_PAGE_PATHS = ['/login', '/join']

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const isFullPage = FULL_PAGE_PATHS.some(p => path === p || path.startsWith(p + '?'))

  return (
    <ThemeProvider>
      <TimezoneProvider>
      <AuthProvider>
        {isFullPage ? (
          children
        ) : (
          <div style={{ display: 'flex', minHeight: '100vh' }}>
            <Sidebar />
            <div style={{
              flex: 1,
              marginLeft: 'var(--sidebar-w)',
              display: 'flex',
              flexDirection: 'column',
              minHeight: '100vh',
              overflow: 'auto',
              background: 'var(--bg)',
            }}>
              {children}
            </div>
          </div>
        )}
      </AuthProvider>
      </TimezoneProvider>
    </ThemeProvider>
  )
}
