'use client'
import { useState, useEffect, useRef } from 'react'
import { Play, Trash2, Film, Plus, Link, FileText, Download, BookOpen, X } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { markOnboarding } from '@/components/OnboardingChecklist'
import UpdatesSection from '@/components/UpdatesSection'

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
        <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>{title}</h2>
      </div>
      <div style={{ padding: '20px' }}>{children}</div>
    </div>
  )
}

function Step({ n, title, body }: { n: number; title: string; body: string }) {
  return (
    <div style={{ display: 'flex', gap: 14, marginBottom: 18 }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
        background: 'var(--accent-bg)', color: 'var(--accent-hover)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontWeight: 700, fontSize: 12,
      }}>{n}</div>
      <div>
        <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{title}</p>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.7 }}>{body}</p>
      </div>
    </div>
  )
}

function Def({ term, def }: { term: string; def: string }) {
  return (
    <div style={{ padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
      <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{term}</p>
      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.7 }}>{def}</p>
    </div>
  )
}

const VARIANT: Record<string, { color: string; bg: string }> = {
  accent:  { color: 'var(--accent)',  bg: 'var(--accent-bg)' },
  warning: { color: 'var(--warning)', bg: 'var(--warning-bg)' },
  bullish: { color: 'var(--bullish)', bg: 'var(--bullish-bg)' },
}

function BoxGrid({ items }: { items: { label: string; variant: string; desc: string }[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
      {items.map(({ label, variant, desc }) => {
        const v = VARIANT[variant] ?? VARIANT.accent
        return (
          <div key={label + desc} style={{ background: v.bg, border: `1px solid ${v.color}30`, borderRadius: 10, padding: 16 }}>
            <p style={{ fontWeight: 700, fontSize: 14, color: v.color, marginBottom: 8 }}>{label}</p>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{desc}</p>
          </div>
        )
      })}
    </div>
  )
}

interface VideoEntry { title: string; url: string }

function toEmbedUrl(url: string): string {
  const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  if (yt) return `https://www.youtube.com/embed/${yt[1]}?rel=0&modestbranding=1`
  const vimeo = url.match(/vimeo\.com\/(\d+)/)
  if (vimeo) return `https://player.vimeo.com/video/${vimeo[1]}`
  return url
}

function authHdrs(): HeadersInit {
  const t = typeof window !== 'undefined' ? localStorage.getItem('mbp_token') : null
  return t ? { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

function VideoSection() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [videos, setVideos] = useState<VideoEntry[]>([])
  const [playing, setPlaying] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    fetch(`${API_BASE}/api/videos`, { headers: authHdrs() })
      .then(r => r.json())
      .then(d => setVideos(Array.isArray(d) ? d : []))
      .catch(() => {})
  }

  useEffect(load, [])

  const add = async () => {
    if (!title.trim() || !url.trim()) return
    setSaving(true); setError('')
    try {
      const res = await fetch(`${API_BASE}/api/videos`, {
        method: 'POST', headers: authHdrs(),
        body: JSON.stringify({ title: title.trim(), url: url.trim() }),
      })
      if (!res.ok) throw new Error('Failed to save')
      setTitle(''); setUrl(''); setShowForm(false); load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally { setSaving(false) }
  }

  const remove = async (v: VideoEntry) => {
    await fetch(`${API_BASE}/api/videos?url=${encodeURIComponent(v.url)}`, {
      method: 'DELETE', headers: authHdrs(),
    })
    setVideos(vs => vs.filter(x => x.url !== v.url))
    if (playing === v.url) setPlaying(null)
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Film size={15} color="var(--accent-hover)" />
          <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Tutorial Videos</h2>
        </div>
        {isOwner && (
          <button onClick={() => setShowForm(f => !f)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: showForm ? 'var(--card-hover)' : 'var(--accent)', color: showForm ? 'var(--text-secondary)' : 'white', border: 'none', cursor: 'pointer' }}>
            {showForm ? 'Cancel' : <><Plus size={12} /> Add video</>}
          </button>
        )}
      </div>

      {isOwner && showForm && (
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>Paste a YouTube or Vimeo link. The video is embedded directly — no files stored on the server.</p>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title (e.g. Origin trade walkthrough)"
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)' }}>
              <Link size={13} color="var(--text-secondary)" />
              <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=... or https://youtu.be/..."
                style={{ flex: 1, background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
            </div>
            <button onClick={add} disabled={saving || !title.trim() || !url.trim()}
              style={{ padding: '8px 18px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, background: 'var(--accent)', color: 'white', opacity: (saving || !title.trim() || !url.trim()) ? 0.5 : 1 }}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
          {error && <p style={{ fontSize: 12, color: 'var(--bearish)' }}>{error}</p>}
        </div>
      )}

      <div style={{ padding: '20px' }}>
        {videos.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <Film size={32} color="var(--text-muted)" style={{ margin: '0 auto 10px' }} />
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>No tutorial videos yet.</p>
            {isOwner && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Add a YouTube or Vimeo link to build your tutorial library.</p>}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {videos.map(v => (
              <div key={v.url} style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: playing === v.url ? '1px solid var(--border)' : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Film size={13} color="var(--text-secondary)" />
                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{v.title}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => { markOnboarding(user?.id, 'video'); setPlaying(p => p === v.url ? null : v.url) }}
                      style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, background: playing === v.url ? 'var(--card-hover)' : 'var(--accent-bg)', color: playing === v.url ? 'var(--text-secondary)' : 'var(--accent-hover)', fontWeight: 500 }}>
                      <Play size={11} />{playing === v.url ? 'Minimise' : 'Watch'}
                    </button>
                    {isOwner && (
                      <button onClick={() => remove(v)}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, borderRadius: 7, border: 'none', cursor: 'pointer', background: 'var(--bearish-bg)', color: 'var(--bearish)' }}>
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
                {playing === v.url && (
                  <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
                    <iframe
                      src={toEmbedUrl(v.url)}
                      style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                      allowFullScreen
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Strategy methodology (owner-only; fetched from the backend) ───────────────

interface DefItem { term: string; body: string }
interface BoxItem { label: string; variant: string; desc: string }
interface StrategyData {
  chain: { n: number; title: string; body: string }[]
  formations: DefItem[]
  h4_classification: BoxItem[]
  daily_context: { intro: string; items: BoxItem[] }
  alert_classifications: DefItem[]
  reaction_sources: DefItem[]
  disclaimer: string
}

// Owner-only PDFs, fetched with the auth header and saved from a blob so the file
// is never at a public URL.
const DOCS = [
  { key: 'rulebook', title: 'Strategy Rulebook', desc: 'Every rule, numbered, with a picture of each condition.', file: 'MummyTKT_Strategy_Rulebook.pdf' },
  { key: 'storybook', title: 'Pip and the Golden Bell', desc: 'The same strategy as a once-upon-a-time bedtime story for children.', file: 'The_Candle_Twins_Storybook.pdf' },
]

// Read a PDF right on the page. Phones (and Telegram's in-app browser) can't show a PDF in
// a frame, so the pages are drawn with pdf.js (loaded once from a CDN) as images.
const PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js'
const PDFJS_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'
type PdfJs = { GlobalWorkerOptions: { workerSrc: string }; getDocument: (o: { data: ArrayBuffer }) => { promise: Promise<{
  numPages: number; getPage: (n: number) => Promise<{
    getViewport: (o: { scale: number }) => { width: number; height: number }
    render: (o: { canvasContext: CanvasRenderingContext2D; viewport: unknown }) => { promise: Promise<void> } }> }> } }
function loadPdfJs(): Promise<PdfJs> {
  const w = window as unknown as { pdfjsLib?: PdfJs }
  if (w.pdfjsLib) return Promise.resolve(w.pdfjsLib)
  return new Promise((resolve, reject) => {
    const sc = document.createElement('script')
    sc.src = PDFJS
    sc.onload = () => { const lib = w.pdfjsLib; if (!lib) return reject(); lib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER; resolve(lib) }
    sc.onerror = reject
    document.head.appendChild(sc)
  })
}

function PdfReader({ data, title, onClose }: { data: ArrayBuffer; title: string; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState('Opening…')
  useEffect(() => {
    let stop = false
    ;(async () => {
      try {
        const lib = await loadPdfJs()
        const doc = await lib.getDocument({ data: data.slice(0) }).promise
        const width = Math.min((box.current?.clientWidth || 800) - 8, 900)
        for (let n = 1; n <= doc.numPages && !stop; n++) {
          const page = await doc.getPage(n)
          const base = page.getViewport({ scale: 1 })
          const ratio = window.devicePixelRatio || 1
          const vp = page.getViewport({ scale: (width / base.width) * ratio })
          const c = document.createElement('canvas')
          c.width = vp.width; c.height = vp.height
          c.style.width = `${width}px`; c.style.display = 'block'; c.style.margin = '0 auto 10px'; c.style.borderRadius = '6px'
          c.style.boxShadow = '0 4px 18px rgba(0,0,0,0.35)'
          const ctx = c.getContext('2d')
          if (!ctx) continue
          await page.render({ canvasContext: ctx, viewport: vp }).promise
          if (stop) return
          box.current?.appendChild(c)
          setStatus(n < doc.numPages ? `Page ${n} of ${doc.numPages}…` : '')
        }
      } catch { if (!stop) setStatus('Couldn’t show this file here. Use Download PDF instead.') }
    })()
    return () => { stop = true }
  }, [data])
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(8,9,18,0.92)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
        <BookOpen size={16} color="white" />
        <span style={{ color: 'white', fontWeight: 700, fontSize: 14, flex: 1 }}>{title}</span>
        {status && <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>{status}</span>}
        <button onClick={onClose} aria-label="Close" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px', borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.25)', background: 'transparent', color: 'white', cursor: 'pointer', fontSize: 12 }}>
          <X size={14} /> Close
        </button>
      </div>
      <div ref={box} style={{ flex: 1, overflowY: 'auto', padding: '14px 4px' }} />
    </div>
  )
}

function StrategyDocs() {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [reading, setReading] = useState<{ title: string; data: ArrayBuffer } | null>(null)

  const read = async (d: typeof DOCS[number]) => {
    setBusy(d.key); setError('')
    try {
      const res = await fetch(`${API_BASE}/api/strategy-docs/${d.key}`, { headers: authHdrs() })
      if (!res.ok) throw new Error('Open failed')
      setReading({ title: d.title, data: await res.arrayBuffer() })
    } catch {
      setError('Couldn’t open that file. Please try again.')
    } finally { setBusy(null) }
  }

  const download = async (d: typeof DOCS[number]) => {
    setBusy(d.key); setError('')
    try {
      const res = await fetch(`${API_BASE}/api/strategy-docs/${d.key}`, { headers: authHdrs() })
      if (!res.ok) throw new Error('Download failed')
      const url = URL.createObjectURL(await res.blob())
      const a = document.createElement('a')
      a.href = url; a.download = d.file
      document.body.appendChild(a); a.click(); a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch {
      setError('Couldn’t download that file. Please try again.')
    } finally { setBusy(null) }
  }

  return (
    <Card title="Strategy Documents">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {DOCS.map(d => (
          <div key={d.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', padding: '12px 14px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: '1 1 220px' }}>
              <FileText size={16} color="var(--accent-hover)" style={{ flexShrink: 0 }} />
              <div style={{ minWidth: 0 }}>
                <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{d.title}</p>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2, lineHeight: 1.5 }}>{d.desc}</p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => read(d)} disabled={busy !== null}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: 'var(--surface)', color: 'var(--text-primary)', border: '1px solid var(--border)', cursor: 'pointer', opacity: busy !== null && busy !== d.key ? 0.5 : 1 }}>
                <BookOpen size={12} />Read
              </button>
              <button onClick={() => download(d)} disabled={busy !== null}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', opacity: busy !== null && busy !== d.key ? 0.5 : 1 }}>
                <Download size={12} />{busy === d.key ? 'Opening…' : 'Download PDF'}
              </button>
            </div>
          </div>
        ))}
        {error && <p style={{ fontSize: 12, color: 'var(--bearish)' }}>{error}</p>}
        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Only you can see these. Subscribers don’t have access.</p>
      </div>
      {reading && <PdfReader title={reading.title} data={reading.data} onClose={() => setReading(null)} />}
    </Card>
  )
}

function StrategyContent() {
  const [data, setData] = useState<StrategyData | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/strategy-content`, { headers: authHdrs() })
      .then(r => (r.ok ? r.json() : null))
      .then(d => setData(d))
      .catch(() => {})
  }, [])

  if (!data) return null

  return (
    <>
      <StrategyDocs />

      <Card title="The 4-Step Confirmation Chain">
        {data.chain.map(s => <Step key={s.n} n={s.n} title={s.title} body={s.body} />)}
      </Card>

      <Card title="Formation Types">
        {data.formations.map(f => <Def key={f.term} term={f.term} def={f.body} />)}
      </Card>

      <Card title="H4 Breakout Classification">
        <BoxGrid items={data.h4_classification} />
      </Card>

      <Card title="Daily Level Context">
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 16 }}>{data.daily_context.intro}</p>
        <BoxGrid items={data.daily_context.items} />
      </Card>

      <Card title="Alert Classifications">
        {data.alert_classifications.map(a => <Def key={a.term} term={a.term} def={a.body} />)}
      </Card>

      <Card title="Reaction Source Types">
        {data.reaction_sources.map(r => <Def key={r.term} term={r.term} def={r.body} />)}
      </Card>

      <div style={{
        display: 'flex', gap: 10, padding: '14px 18px', borderRadius: 10,
        background: 'var(--warning-bg)', border: '1px solid var(--warning-bg)',
        fontSize: 12, color: 'var(--text-secondary)', alignItems: 'flex-start',
      }}>
        <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
        <span style={{ lineHeight: 1.7 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Directional bias only — not an entry signal.</strong>
          {' '}{data.disclaimer}
        </span>
      </div>
    </>
  )
}

export default function StrategyPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  return (
    <>
      <TopBar title={isOwner ? 'Strategy' : 'Playbook'} subtitle={isOwner ? 'How the engine detects and confirms directional bias' : 'Updates, tutorial videos and walkthroughs'} />
      <main style={{ flex: 1, width: '100%', padding: '24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
        <UpdatesSection />
        <VideoSection />
        {isOwner && <StrategyContent />}
      </main>
    </>
  )
}
