'use client'
import { useState, useEffect, useRef } from 'react'
import { Upload, Play, Trash2, Film } from 'lucide-react'
import TopBar from '@/components/TopBar'
import { API_BASE } from '@/lib/api'
import { useAuth } from '@/lib/auth'

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

function VideoSection() {
  const { user } = useAuth()
  const isOwner = user?.role === 'OWNER'
  const [videos, setVideos] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [playing, setPlaying] = useState<string | null>(null)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const load = () => {
    fetch(`${API_BASE}/api/videos`)
      .then(r => r.json())
      .then(d => setVideos(d.videos ?? []))
      .catch(() => {})
  }

  useEffect(load, [])

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API_BASE}/api/videos`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error('Upload failed')
      load()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const remove = async (name: string) => {
    await fetch(`${API_BASE}/api/videos/${encodeURIComponent(name)}`, { method: 'DELETE' })
    setVideos(v => v.filter(f => f !== name))
    if (playing === name) setPlaying(null)
  }

  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Film size={15} color="var(--accent-hover)" />
          <h2 style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>Tutorial Videos</h2>
        </div>
        {isOwner && (
          <label style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600,
            background: 'var(--accent)', color: 'white', cursor: 'pointer',
            opacity: uploading ? 0.6 : 1,
          }}>
            <Upload size={12} />
            {uploading ? 'Uploading…' : 'Upload video'}
            <input ref={inputRef} type="file" accept="video/*" style={{ display: 'none' }} onChange={upload} disabled={uploading} />
          </label>
        )}
      </div>
      <div style={{ padding: '20px' }}>
        {error && (
          <p style={{ fontSize: 12, color: 'var(--bearish)', marginBottom: 12 }}>{error}</p>
        )}
        {videos.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <Film size={32} color="var(--text-muted)" style={{ margin: '0 auto 10px' }} />
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>No tutorial videos yet.</p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Upload MP4, WebM or MOV files to build your tutorial library.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {videos.map(name => (
              <div key={name} style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: playing === name ? '1px solid var(--border)' : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Film size={13} color="var(--text-secondary)" />
                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{name}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => setPlaying(p => p === name ? null : name)}
                      style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, background: playing === name ? 'var(--card-hover)' : 'var(--accent-bg)', color: playing === name ? 'var(--text-secondary)' : 'var(--accent-hover)', fontWeight: 500 }}>
                      <Play size={11} />
                      {playing === name ? 'Minimise' : 'Play'}
                    </button>
                    {isOwner && (
                      <button onClick={() => remove(name)}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, borderRadius: 7, border: 'none', cursor: 'pointer', background: 'var(--bearish-bg)', color: 'var(--bearish)' }}>
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
                {playing === name && (
                  <video controls style={{ width: '100%', display: 'block', maxHeight: 400 }}>
                    <source src={`${API_BASE}/api/videos/${encodeURIComponent(name)}`} />
                    Your browser does not support the video tag.
                  </video>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function StrategyPage() {
  return (
    <>
      <TopBar title="Strategy" subtitle="How the engine detects and confirms directional bias" />
      <main style={{ flex: 1, padding: '24px', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 20 }}>

        <VideoSection />

        <Card title="The 4-Step Confirmation Chain">
          <Step n={1} title="Daily Breakout" body="The engine identifies A-shapes (bearish resistance) and V-shapes (bullish support) on the Daily chart using body-only levels — never wicks. A breakout occurs when a Daily candle closes beyond the most recent A or V body level." />
          <Step n={2} title="Reaction Source Identification" body="After a breakout, the engine identifies up to 4 types of reaction sources: the Daily Breaker level, OC levels inside the pre-breakout range, A/V levels inside the range, and post-breakout OC levels. These become the zones price must retest." />
          <Step n={3} title="Retest Detection" body="When an H4 candle's high or low (including wicks) touches any active reaction source band, the engine flags a retest in progress. The band is the source level ± the configured tolerance (default 5 pips)." />
          <Step n={4} title="H4 Confirmation" body="With a retest in progress, the engine checks subsequent H4 candles for a qualifying H4 A-shape or V-shape breakout that closes beyond the body level. This confirms directional alignment between the Daily and H4 timeframes, triggering the alert." />
        </Card>

        <Card title="Formation Types">
          <Def term="A-Shape (Bearish resistance)"
            def="Two consecutive Daily candles where candle 1 is bullish and candle 2 is bearish. The level is candle 1's body high (max of open/close, never the wick)." />
          <Def term="V-Shape (Bullish support)"
            def="Two consecutive Daily candles where candle 1 is bearish and candle 2 is bullish. The level is candle 1's body low (min of open/close, never the wick)." />
          <Def term="OC (Open-Close level)"
            def="Formed when 2+ consecutive same-direction candles run. Each consecutive pair produces an OC level at the midpoint of their two closes. A run of 3 candles produces exactly 2 independent OC levels." />
        </Card>

        <Card title="H4 Breakout Classification">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {[
              { label: 'External', color: 'var(--accent)', bg: 'var(--accent-bg)', desc: 'The H4 candle closes beyond the outermost H4 formation — the swing boundary. This is the conservative confirmation.' },
              { label: 'Internal', color: 'var(--warning)', bg: 'var(--warning-bg)', desc: 'The H4 candle closes beyond an inner H4 formation that formed after the outer swing. This is an earlier, more aggressive confirmation.' },
            ].map(({ label, color, bg, desc }) => (
              <div key={label} style={{ background: bg, border: `1px solid ${color}30`, borderRadius: 10, padding: 16 }}>
                <p style={{ fontWeight: 700, fontSize: 14, color, marginBottom: 8 }}>{label}</p>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{desc}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Alert Classifications">
          <Def
            term="Origin"
            def="The first confirmed bias alert for a setup. Requires the complete 4-step chain: Daily breakout → eligible reaction source → retest of that source → qualifying H4 A/V breakout. After an Origin fires, the engine enters continuation mode for that instrument." />
          <Def
            term="Continuation — A/V Break"
            def="Fires after an Origin, when a subsequent H4 A-shape (bullish direction) or V-shape (bearish direction) formation is broken in the daily breakout direction — without needing a new Daily source retest. Each continuation extends the active bias confirmation. Active until a new opposing Daily breakout occurs." />
          <Def
            term="Continuation — H4 OC"
            def="Fires when two consecutive same-direction H4 candles form an OC level, and price returns to react from the OC midpoint: the H4 candle's range dips into the OC zone and the candle closes beyond the midpoint in the breakout direction. Confirms continuation of the established Daily bias without requiring a new A/V break." />
        </Card>

        <Card title="Reaction Source Types">
          {[
            { label: 'Daily Breaker', desc: 'The original A or V body level that was broken. Price often returns to test it from the other side (role reversal).' },
            { label: 'OC Inside Range', desc: 'An OC level that formed inside the pre-breakout range, in the direction of the breakout. Filtered to those between the broken level and the nearest swing extreme.' },
            { label: 'A/V Inside Range', desc: 'After a bearish breakout: A-shapes inside the range. After a bullish breakout: V-shapes inside the range.' },
            { label: 'Post-Breakout OC', desc: 'Two consecutive same-direction Daily candles after the breakout candle, in the breakout direction. The midpoint of their closes becomes a reaction zone.' },
          ].map(({ label, desc }) => (
            <Def key={label} term={label} def={desc} />
          ))}
        </Card>

        <div style={{
          display: 'flex', gap: 10, padding: '14px 18px', borderRadius: 10,
          background: 'var(--warning-bg)', border: '1px solid var(--warning-bg)',
          fontSize: 12, color: 'var(--text-secondary)', alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
          <span style={{ lineHeight: 1.7 }}>
            <strong style={{ color: 'var(--text-primary)' }}>Directional bias only — not an entry signal.</strong>
            {' '}Alerts confirm Daily + H4 alignment. Entry timing, risk management, and position sizing remain your responsibility.
          </span>
        </div>

      </main>
    </>
  )
}
