'use client'
import { useEffect, useRef, useState } from 'react'
import { autoSlash, parseTyped, showTyped } from '@/lib/dateInput'

// Every date box on the site: type dd/mm/yy (the slashes go in by themselves), or use the calendar button.
export default function DateInput({ value, onChange, withTime, min, placeholder, style, fill }: {
  value: string | null | undefined
  onChange: (v: string) => void
  withTime?: boolean
  min?: string
  placeholder?: string
  style?: React.CSSProperties
  fill?: boolean     // take the whole width of the form column
}) {
  const [text, setText] = useState(showTyped(value))
  const [bad, setBad] = useState(false)
  const pick = useRef<HTMLInputElement>(null)
  useEffect(() => { setText(showTyped(value)); setBad(false) }, [value])
  const commit = () => {
    const v = parseTyped(text, !!withTime)
    if (v === null || (v && min && v.slice(0, 10) < min.slice(0, 10))) { setBad(true); return }
    setBad(false)
    if (v !== (value || '')) onChange(v)
    else setText(showTyped(value))
  }
  return (
    <span style={{ display: fill ? 'flex' : 'inline-flex', alignItems: 'center', gap: 4, flexWrap: 'wrap', position: 'relative' }}>
      <input value={text} placeholder={placeholder || (withTime ? 'dd/mm/yy hh:mm' : 'dd/mm/yy')}
        title={'Type the date as dd/mm/yy, for example 06/01/20' + (withTime ? ', with a time like 14:00' : '')}
        onChange={e => { setText(autoSlash(e.target.value, text, !!withTime)); setBad(false) }} onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur() } }}
        style={{ ...style, ...(fill ? { flex: 1, width: 'auto', minWidth: 0 } : { width: withTime ? 150 : 112 }), ...(bad ? { borderColor: 'var(--bearish)' } : {}) }} />
      <button type="button" title="Pick from a calendar" onClick={() => { try { pick.current?.showPicker() } catch { pick.current?.click() } }}
        style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 14, padding: 2, color: 'var(--text-muted)' }}>📅</button>
      <input ref={pick} type={withTime ? 'datetime-local' : 'date'} value={value || ''} min={min} tabIndex={-1} aria-hidden
        onChange={e => onChange(e.target.value)}
        style={{ position: 'absolute', opacity: 0, width: 1, height: 1, pointerEvents: 'none' }} />
      {bad && <span style={{ fontSize: 11, color: 'var(--bearish)' }}>not a date{min ? ' (or before the entry)' : ''}</span>}
    </span>
  )
}
