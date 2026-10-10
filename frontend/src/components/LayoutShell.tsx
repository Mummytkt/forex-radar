'use client'
import { usePathname } from 'next/navigation'
import { createContext, useContext, useState, useCallback } from 'react'
import { ThemeProvider } from '@/lib/theme'
import { AuthProvider } from '@/lib/auth'
import { TimezoneProvider } from '@/lib/timezone'
import Sidebar from './Sidebar'

interface SidebarCtx { open: boolean; toggle: () => void; close: () => void }
const SidebarContext = createContext<SidebarCtx>({ open: false, toggle: () => {}, close: () => {} })
export const useSidebar = () => useContext(SidebarContext)

const FULL_PAGE_PATHS = ['/login', '/join']

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const isFullPage = FULL_PAGE_PATHS.some(p => path === p || path.startsWith(p + '?'))
  const [open, setOpen] = useState(false)
  const toggle = useCallback(() => setOpen(v => !v), [])
  const close = useCallback(() => setOpen(false), [])

  return (
    <ThemeProvider>
      <TimezoneProvider>
        <AuthProvider>
          <SidebarContext.Provider value={{ open, toggle, close }}>
            {isFullPage ? (
              children
            ) : (
              <div style={{ display: 'flex', minHeight: '100vh' }}>
                <Sidebar />
                {open && (
                  <div
                    onClick={close}
                    className="mobile-only"
                    style={{
                      position: 'fixed', inset: 0,
                      background: 'rgba(0,0,0,0.55)',
                      zIndex: 25,
                    }}
                  />
                )}
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
          </SidebarContext.Provider>
        </AuthProvider>
      </TimezoneProvider>
    </ThemeProvider>
  )
}
