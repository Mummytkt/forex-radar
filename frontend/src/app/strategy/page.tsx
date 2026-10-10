import TopBar from '@/components/TopBar'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl p-6" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <h2 className="font-bold text-base mb-4" style={{ color: 'var(--text-primary)' }}>{title}</h2>
      {children}
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white mt-0.5"
        style={{ background: 'var(--accent)' }}>{n}</div>
      <div>
        <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>{title}</p>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{children}</p>
      </div>
    </div>
  )
}

function Formation({ name, color, desc, rule }: { name: string; color: string; desc: string; rule: string }) {
  return (
    <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: `1px solid ${color}44` }}>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full" style={{ background: color }} />
        <span className="font-bold text-sm" style={{ color }}>{name}</span>
      </div>
      <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>{desc}</p>
      <p className="text-xs px-2 py-1 rounded font-mono" style={{ background: 'var(--card)', color: 'var(--text-primary)' }}>
        {rule}
      </p>
    </div>
  )
}

export default function StrategyPage() {
  return (
    <>
      <TopBar title="Strategy Guide" />
      <main className="flex-1 p-6 space-y-5 max-w-3xl">

        <Section title="How Bias Radar Works">
          <p className="text-sm leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
            Bias Radar monitors 37 forex and crypto instruments 24/7. It detects specific candle formations on the
            Daily chart, tracks when price breaks key structural levels, and confirms the move with an H4 breakout
            in the same direction. Only when all four conditions align does an alert fire.
          </p>
          <div className="space-y-4">
            <Step n={1} title="Daily Formation Detected">
              The engine scans every Daily candle for A-shapes (resistance) and V-shapes (support). These formations
              define the key structural levels the market respects.
            </Step>
            <Step n={2} title="Daily Breakout Confirmed">
              When a Daily candle closes strictly beyond the body level of the most recent formation, a breakout is
              recorded. Wick-only moves never qualify — only body closes count.
            </Step>
            <Step n={3} title="Reaction Source Retested">
              After a breakout, the engine identifies eligible reaction sources: the broken level (now role-reversed),
              OC levels inside the range, A/V levels inside the range, and post-breakout OC levels. When price retraces
              into any source's tolerance band, retest monitoring begins.
            </Step>
            <Step n={4} title="H4 Breakout Confirms">
              During retest, every H4 candle close is checked. If an H4 candle closes beyond the body level of an H4
              A-shape (bullish) or V-shape (bearish) in the same direction as the Daily breakout, the alert fires.
            </Step>
          </div>
        </Section>

        <Section title="Candle Formations">
          <div className="grid sm:grid-cols-2 gap-4">
            <Formation
              name="A-Shape (Resistance)"
              color="#EF4444"
              desc="A bullish candle followed immediately by a bearish candle. The body_high of the bullish candle becomes the resistance level."
              rule="candle[i] bullish → candle[i+1] bearish  |  level = body_high[i]"
            />
            <Formation
              name="V-Shape (Support)"
              color="#10B981"
              desc="A bearish candle followed immediately by a bullish candle. The body_low of the bearish candle becomes the support level."
              rule="candle[i] bearish → candle[i+1] bullish  |  level = body_low[i]"
            />
            <Formation
              name="OC Level (Order Close)"
              color="#6366F1"
              desc="Two consecutive same-direction candles. Their closing price midpoint becomes a reaction level. A run of 3 candles produces 2 OC levels."
              rule="level = (close[i] + close[i+1]) / 2"
            />
            <Formation
              name="Post-Breakout OC"
              color="#F59E0B"
              desc="Two consecutive same-direction Daily candles after the breakout, moving in the breakout direction. Their OC midpoint is an eligible reaction source."
              rule="Forms after breakout candle, direction must match breakout"
            />
          </div>
        </Section>

        <Section title="Reaction Sources">
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
            After every Daily breakout, four types of reaction sources are computed:
          </p>
          <div className="space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
            {[
              ['Daily Breaker', 'The original A-shape or V-shape level that was broken. Role-reversed — former resistance becomes support and vice versa.'],
              ['OC Inside Range', 'OC levels that formed before the breakout candle, between the broken level and the swing extreme. Direction must match the breakout.'],
              ['A/V Inside Range', 'A-shapes (bearish breakout) or V-shapes (bullish breakout) inside the pre-breakout range.'],
              ['Post-Breakout OC', 'Two consecutive same-direction Daily candles after the breakout, moving in the breakout direction.'],
            ].map(([name, desc]) => (
              <div key={name} className="flex gap-3">
                <span className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" style={{ background: 'var(--accent)' }} />
                <div><span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{name} — </span>{desc}</div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="H4 Confirmation: External vs Internal">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Every qualifying H4 breakout is classified as either <strong style={{ color: 'var(--text-primary)' }}>External</strong> or <strong style={{ color: 'var(--text-primary)' }}>Internal</strong>:
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mt-4">
            <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <p className="font-semibold text-sm mb-2" style={{ color: '#818CF8' }}>External</p>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                The H4 candle breaks the first (oldest) structural H4 formation in the current leg. This is the
                strongest confirmation — it breaks the outer swing boundary.
              </p>
            </div>
            <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <p className="font-semibold text-sm mb-2" style={{ color: '#FCD34D' }}>Internal</p>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                The H4 candle breaks a smaller formation that developed after the outer boundary — internal to the
                current move. Still valid, but signals a shorter-range structure break.
              </p>
            </div>
          </div>
        </Section>

        <Section title="Important Disclaimer">
          <div className="rounded-lg p-4" style={{ background: '#F59E0B11', border: '1px solid #F59E0B44' }}>
            <p className="text-sm leading-relaxed" style={{ color: '#FCD34D' }}>
              Bias Radar provides <strong>directional bias only</strong> — not entry signals. A confirmed alert
              tells you the Daily and H4 are aligned in a direction. It does not tell you where to enter, stop,
              or target. Always apply your own entry model and risk management. Past alerts are not indicative
              of future performance.
            </p>
          </div>
        </Section>

      </main>
    </>
  )
}
