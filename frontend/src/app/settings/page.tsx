'use client'
import { useState } from 'react'
import { Send, CheckCircle, XCircle, Info } from 'lucide-react'
import TopBar from '@/components/TopBar'

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex items-start justify-between py-3 border-b last:border-0"
      style={{ borderColor: 'var(--border)' }}>
      <div>
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{label}</p>
        {note && <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{note}</p>}
      </div>
      <span className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  )
}

export default function SettingsPage() {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'ok' | 'fail' | null>(null)

  const sendTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? 'https://forex-radar.fly.dev'
      const res = await fetch(`${base}/api/telegram/test`, { method: 'POST' })
      setTestResult(res.ok ? 'ok' : 'fail')
    } catch {
      setTestResult('fail')
    } finally {
      setTesting(false)
    }
  }

  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 p-6 space-y-5 max-w-2xl">

        {/* Telegram */}
        <div className="rounded-xl p-6" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <h2 className="font-bold text-base mb-1" style={{ color: 'var(--text-primary)' }}>Telegram Alerts</h2>
          <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
            Alerts are sent via your Telegram bot when all 4 conditions are confirmed.
          </p>
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            <Row label="Bot token" value="configured ✓" note="Set via TELEGRAM_BOT_TOKEN env variable" />
            <Row label="Chat ID" value="configured ✓" note="Set via TELEGRAM_CHAT_ID env variable" />
            <Row label="Delivery" value="enabled" note="Alerts fire automatically on confirmation" />
          </div>
          <div className="mt-5 flex items-center gap-3">
            <button onClick={sendTest} disabled={testing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
              style={{ background: 'var(--accent)', color: 'white' }}>
              <Send size={14} />
              {testing ? 'Sending…' : 'Send Test Message'}
            </button>
            {testResult === 'ok' && (
              <span className="flex items-center gap-1.5 text-sm" style={{ color: '#10B981' }}>
                <CheckCircle size={14} /> Delivered successfully
              </span>
            )}
            {testResult === 'fail' && (
              <span className="flex items-center gap-1.5 text-sm" style={{ color: '#EF4444' }}>
                <XCircle size={14} /> Failed — check bot token and chat ID
              </span>
            )}
          </div>
        </div>

        {/* Engine settings */}
        <div className="rounded-xl p-6" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <h2 className="font-bold text-base mb-1" style={{ color: 'var(--text-primary)' }}>Engine Configuration</h2>
          <p className="text-sm mb-5" style={{ color: 'var(--text-secondary)' }}>
            These values are set via environment variables on the server.
          </p>
          <div>
            <Row label="Tolerance band" value="5 pips" note="Reaction source tolerance for retest detection" />
            <Row label="Daily lookback" value="200 candles" note="Historical candles fetched on startup" />
            <Row label="H4 lookback" value="500 candles" note="Historical H4 candles fetched on startup" />
            <Row label="H4 schedule" value="00:05, 04:05, 08:05, 12:05, 16:05, 20:05 UTC" note="Jobs fire 5 min after each 4h close" />
            <Row label="Daily schedule" value="21:05 + 22:05 UTC" note="Dual-fire covers EDT and EST daily close" />
          </div>
        </div>

        {/* Instruments */}
        <div className="rounded-xl p-6" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <h2 className="font-bold text-base mb-1" style={{ color: 'var(--text-primary)' }}>Monitored Instruments</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
            37 instruments are currently monitored. Forex pairs are active during market hours; crypto runs 24/7.
          </p>
          <div className="flex items-start gap-2 p-3 rounded-lg text-xs"
            style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
            <Info size={13} className="mt-0.5 flex-shrink-0" />
            <span>To add or remove instruments, update the <code className="font-mono">INSTRUMENTS</code> environment
              variable in your Fly.io dashboard, then redeploy. Or edit <code className="font-mono">config.py</code> directly.</span>
          </div>
        </div>

      </main>
    </>
  )
}
