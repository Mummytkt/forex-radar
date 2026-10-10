'use client'
import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const TZ_KEY = 'mbp_tz'

export interface TZEntry {
  zone: string
  label: string
  region: string
}

export const TIMEZONES: TZEntry[] = [
  { zone: 'UTC',                 label: 'UTC — Coordinated Universal Time', region: 'Universal' },
  // Africa
  { zone: 'Africa/Accra',        label: 'Accra / Abidjan',          region: 'Africa' },
  { zone: 'Africa/Lagos',        label: 'Lagos / Abuja / Kano',     region: 'Africa' },
  { zone: 'Africa/Cairo',        label: 'Cairo',                    region: 'Africa' },
  { zone: 'Africa/Johannesburg', label: 'Johannesburg / Cape Town', region: 'Africa' },
  { zone: 'Africa/Nairobi',      label: 'Nairobi / Addis Ababa',    region: 'Africa' },
  { zone: 'Africa/Casablanca',   label: 'Casablanca',               region: 'Africa' },
  { zone: 'Africa/Lusaka',       label: 'Lusaka / Harare',          region: 'Africa' },
  // Europe
  { zone: 'Europe/London',       label: 'London',                   region: 'Europe' },
  { zone: 'Europe/Paris',        label: 'Paris / Berlin / Madrid',  region: 'Europe' },
  { zone: 'Europe/Athens',       label: 'Athens / Helsinki',        region: 'Europe' },
  { zone: 'Europe/Moscow',       label: 'Moscow',                   region: 'Europe' },
  { zone: 'Europe/Istanbul',     label: 'Istanbul',                 region: 'Europe' },
  // Americas
  { zone: 'America/New_York',    label: 'New York (ET)',            region: 'Americas' },
  { zone: 'America/Chicago',     label: 'Chicago (CT)',             region: 'Americas' },
  { zone: 'America/Denver',      label: 'Denver (MT)',              region: 'Americas' },
  { zone: 'America/Los_Angeles', label: 'Los Angeles (PT)',         region: 'Americas' },
  { zone: 'America/Sao_Paulo',   label: 'São Paulo',                region: 'Americas' },
  { zone: 'America/Toronto',     label: 'Toronto (ET)',             region: 'Americas' },
  // Middle East & Asia
  { zone: 'Asia/Dubai',          label: 'Dubai / Abu Dhabi',        region: 'Asia' },
  { zone: 'Asia/Riyadh',         label: 'Riyadh / Kuwait',          region: 'Asia' },
  { zone: 'Asia/Kolkata',        label: 'Mumbai / Kolkata (IST)',   region: 'Asia' },
  { zone: 'Asia/Dhaka',          label: 'Dhaka (BST)',              region: 'Asia' },
  { zone: 'Asia/Bangkok',        label: 'Bangkok / Jakarta',        region: 'Asia' },
  { zone: 'Asia/Singapore',      label: 'Singapore / Kuala Lumpur', region: 'Asia' },
  { zone: 'Asia/Hong_Kong',      label: 'Hong Kong / Shanghai',     region: 'Asia' },
  { zone: 'Asia/Tokyo',          label: 'Tokyo',                    region: 'Asia' },
  { zone: 'Asia/Seoul',          label: 'Seoul',                    region: 'Asia' },
  // Pacific
  { zone: 'Australia/Sydney',    label: 'Sydney / Melbourne',       region: 'Pacific' },
  { zone: 'Pacific/Auckland',    label: 'Auckland',                 region: 'Pacific' },
]

export function getAbbrStr(tz: string): string {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'short' }).formatToParts(new Date())
    return parts.find(p => p.type === 'timeZoneName')?.value ?? tz
  } catch { return tz }
}

export function getOffsetStr(tz: string): string {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', { timeZone: tz, timeZoneName: 'shortOffset' }).formatToParts(new Date())
    return parts.find(p => p.type === 'timeZoneName')?.value ?? ''
  } catch { return '' }
}

function parseISO(iso: string): Date {
  // Ensure the string is treated as UTC if no offset provided
  if (!iso.endsWith('Z') && !iso.includes('+') && !/T.*-\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso + 'Z')
  }
  return new Date(iso)
}

interface TZCtx {
  timezone: string
  setTimezone: (tz: string) => void
  fmtDate: (iso: string | null) => string
  abbr: string
}

const Ctx = createContext<TZCtx>({
  timezone: 'UTC',
  setTimezone: () => {},
  fmtDate: (iso) => {
    if (!iso) return '—'
    try { return parseISO(iso).toLocaleString('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' UTC' }
    catch { return '—' }
  },
  abbr: 'UTC',
})

export function TimezoneProvider({ children }: { children: React.ReactNode }) {
  const [timezone, setTZ] = useState('UTC')

  useEffect(() => {
    const saved = localStorage.getItem(TZ_KEY)
    if (saved) {
      setTZ(saved)
    } else {
      // Auto-detect browser timezone
      const detected = Intl.DateTimeFormat().resolvedOptions().timeZone
      if (detected) setTZ(detected)
    }
  }, [])

  const setTimezone = useCallback((tz: string) => {
    setTZ(tz)
    localStorage.setItem(TZ_KEY, tz)
  }, [])

  const fmtDate = useCallback((iso: string | null): string => {
    if (!iso) return '—'
    try {
      const d = parseISO(iso)
      return d.toLocaleString('en-GB', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
        timeZone: timezone,
      }) + ' ' + getAbbrStr(timezone)
    } catch { return '—' }
  }, [timezone])

  const abbr = getAbbrStr(timezone)

  return (
    <Ctx.Provider value={{ timezone, setTimezone, fmtDate, abbr }}>
      {children}
    </Ctx.Provider>
  )
}

export const useTimezone = () => useContext(Ctx)
