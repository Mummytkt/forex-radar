import type { Metadata } from 'next'
import './globals.css'
import LayoutShell from '@/components/LayoutShell'

export const metadata: Metadata = {
  title: "MummyTKT's Bias Pointer",
  description: 'Rules-based forex and crypto directional bias alerts',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `try{var t=localStorage.getItem('theme');document.documentElement.setAttribute('data-theme',t||'dark')}catch(e){}` }} />
      </head>
      <body>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  )
}
