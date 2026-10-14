import type { Metadata } from 'next'
import './globals.css'
import LayoutShell from '@/components/LayoutShell'

export const metadata: Metadata = {
  title: "MummyTKT's Bias Pointer",
  description: 'Rules-based forex and crypto directional bias alerts',
}

// Inline script: runs before React hydrates to prevent flash of wrong theme/accent.
// Each entry: [accent, hover, accentBg, pageBg, surface, card, cardHover, border, borderBright]
const INIT_SCRIPT = `try{
  var t=localStorage.getItem('theme')||'dark';
  document.documentElement.setAttribute('data-theme',t);
  var p={
    indigo:{dark:['#6366F1','#818CF8','rgba(99,102,241,0.12)','#090A14','#0F1120','#131526','#181A30','#1C1E35','#272A48'],light:['#4F46E5','#4338CA','rgba(79,70,229,0.09)','#EFF1FB','#FFFFFF','#FFFFFF','#F5F7FF','#DDE1EF','#C8CEEA']},
    emerald:{dark:['#10B981','#34D399','rgba(16,185,129,0.12)','#050F09','#091A0F','#0C2014','#0F2719','#122C1E','#1A402C'],light:['#059669','#047857','rgba(5,150,105,0.09)','#F0FAF5','#FFFFFF','#FFFFFF','#F3FBF7','#C6E9D8','#A8D9C2']},
    sky:{dark:['#0EA5E9','#38BDF8','rgba(14,165,233,0.12)','#050C13','#09141F','#0B1A28','#0E2130','#112638','#1A384E'],light:['#0284C7','#0369A1','rgba(2,132,199,0.09)','#EFF8FF','#FFFFFF','#FFFFFF','#F2F9FF','#C5DFF0','#A4CCDF']},
    purple:{dark:['#A855F7','#C084FC','rgba(168,85,247,0.12)','#0C0912','#150E1C','#1B1224','#22162D','#291A36','#3C264E'],light:['#9333EA','#7E22CE','rgba(147,51,234,0.09)','#F5F0FF','#FFFFFF','#FFFFFF','#F9F5FF','#DDC8F0','#C9ABE5']},
    amber:{dark:['#F59E0B','#FCD34D','rgba(245,158,11,0.12)','#120E05','#1D1609','#251C0B','#2D220E','#362811','#4D3A18'],light:['#D97706','#B45309','rgba(217,119,6,0.09)','#FFFBF0','#FFFFFF','#FFFFFF','#FFFDF5','#EFD898','#E0C070']},
    rose:{dark:['#FB7185','#FDA4AF','rgba(251,113,133,0.12)','#120608','#1E0B0F','#260E14','#2E1119','#38141F','#501D2C'],light:['#E11D48','#BE123C','rgba(225,29,72,0.09)','#FFF0F3','#FFFFFF','#FFFFFF','#FFF5F7','#F0C0CA','#E0A0B0']},
    cyan:{dark:['#06B6D4','#22D3EE','rgba(6,182,212,0.12)','#04100F','#081B1A','#0A2221','#0D2A29','#103130','#184644'],light:['#0891B2','#0E7490','rgba(8,145,178,0.09)','#EDFAFD','#FFFFFF','#FFFFFF','#F2FBFE','#B8E4ED','#90D0DF']},
    orange:{dark:['#F97316','#FB923C','rgba(249,115,22,0.12)','#120A04','#1D1108','#25160A','#2D1B0D','#362010','#4D2E17'],light:['#EA580C','#C2410C','rgba(234,88,12,0.09)','#FFF7F0','#FFFFFF','#FFFFFF','#FFFAF5','#F0D0B0','#E0B888']}
  };
  var id=localStorage.getItem('mbp_accent');
  var s=p[id];
  if(s){var v=s[t]||s.dark;var r=document.documentElement;
    r.style.setProperty('--accent',v[0]);r.style.setProperty('--accent-hover',v[1]);r.style.setProperty('--accent-bg',v[2]);
    r.style.setProperty('--bg',v[3]);r.style.setProperty('--surface',v[4]);r.style.setProperty('--card',v[5]);
    r.style.setProperty('--card-hover',v[6]);r.style.setProperty('--border',v[7]);r.style.setProperty('--border-bright',v[8]);
  }
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
