import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'Bias Radar — Forex Analysis Engine',
  description: 'Rules-based forex and crypto bias alerts',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex" style={{ background: 'var(--bg)' }}>
        <Sidebar />
        <div className="flex-1 ml-56 flex flex-col min-h-screen overflow-auto">
          {children}
        </div>
      </body>
    </html>
  )
}
