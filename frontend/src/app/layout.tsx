import type { Metadata } from 'next'
import './globals.css'
import LayoutShell from '@/components/LayoutShell'

export const metadata: Metadata = {
  title: "MummyTKT's Bias Pointer",
  description: 'Rules-based forex and crypto directional bias alerts',
}

// Inline script: runs before React hydrates to prevent flash of wrong theme/accent
const INIT_SCRIPT = `try{
  var t=localStorage.getItem('theme')||'dark';
  document.documentElement.setAttribute('data-theme',t);
  var p={indigo:{dark:['#6366F1','#818CF8','rgba(99,102,241,0.12)'],light:['#4F46E5','#4338CA','rgba(79,70,229,0.09)']},emerald:{dark:['#10B981','#34D399','rgba(16,185,129,0.12)'],light:['#059669','#047857','rgba(5,150,105,0.09)']},sky:{dark:['#0EA5E9','#38BDF8','rgba(14,165,233,0.12)'],light:['#0284C7','#0369A1','rgba(2,132,199,0.09)']},purple:{dark:['#A855F7','#C084FC','rgba(168,85,247,0.12)'],light:['#9333EA','#7E22CE','rgba(147,51,234,0.09)']},amber:{dark:['#F59E0B','#FCD34D','rgba(245,158,11,0.12)'],light:['#D97706','#B45309','rgba(217,119,6,0.09)']},rose:{dark:['#FB7185','#FDA4AF','rgba(251,113,133,0.12)'],light:['#E11D48','#BE123C','rgba(225,29,72,0.09)']},cyan:{dark:['#06B6D4','#22D3EE','rgba(6,182,212,0.12)'],light:['#0891B2','#0E7490','rgba(8,145,178,0.09)']},orange:{dark:['#F97316','#FB923C','rgba(249,115,22,0.12)'],light:['#EA580C','#C2410C','rgba(234,88,12,0.09)']}};
  var id=localStorage.getItem('mbp_accent');
  var s=p[id];
  if(s){var v=s[t]||s.dark;var r=document.documentElement;r.style.setProperty('--accent',v[0]);r.style.setProperty('--accent-hover',v[1]);r.style.setProperty('--accent-bg',v[2]);}
}catch(e){}`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: INIT_SCRIPT }} />
      </head>
      <body>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  )
}
