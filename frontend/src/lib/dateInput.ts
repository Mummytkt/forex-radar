// Typed dates: always day first, dd/mm/yy. Stored as YYYY-MM-DD or YYYY-MM-DDTHH:MM.
const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const pad2 = (n: number) => String(n).padStart(2, '0')
const fullYear = (s: string) => (+s >= 100 ? +s : +s < 90 ? 2000 + +s : 1900 + +s)

/** The stored date for what was typed: '' when empty, null when it isn't a date. */
export function parseTyped(raw: string, withTime: boolean): string | null {
  const t = raw.trim().toLowerCase().replace(/,/g, ' ').replace(/\s+/g, ' ')
  if (!t) return ''
  let y = 0, m = 0, d = 0, hh = 0, mi = 0
  const tm = /(\d{1,2}):(\d{2})\s*(am|pm)?/.exec(t)
  if (tm) {
    hh = +tm[1]; mi = +tm[2]
    if (tm[3] === 'pm' && hh < 12) hh += 12
    if (tm[3] === 'am' && hh === 12) hh = 0
  }
  const datePart = tm ? t.replace(tm[0], ' ').trim() : t
  let mt
  if ((mt = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/.exec(datePart))) { y = +mt[1]; m = +mt[2]; d = +mt[3] }
  else if ((mt = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})(?!\d)/.exec(datePart))) { d = +mt[1]; m = +mt[2]; y = fullYear(mt[3]) }
  else if ((mt = /^(\d{1,2})\s*([a-z]{3,})\s*(\d{2}|\d{4})$/.exec(datePart))) { d = +mt[1]; m = MONTHS.indexOf(mt[2].slice(0, 3)) + 1; y = fullYear(mt[3]) }
  else if ((mt = /^([a-z]{3,})\s*(\d{1,2})\s+(\d{2}|\d{4})$/.exec(datePart))) { m = MONTHS.indexOf(mt[1].slice(0, 3)) + 1; d = +mt[2]; y = fullYear(mt[3]) }
  else return null
  const dt = new Date(Date.UTC(y, m - 1, d))
  if (!m || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d || y < 1990 || y > 2100 || hh > 23 || mi > 59) return null
  const date = `${y}-${pad2(m)}-${pad2(d)}`
  return withTime && tm ? `${date}T${pad2(hh)}:${pad2(mi)}` : date
}

/** A stored date as dd/mm/yy (with hh:mm when it has a time). */
export function showTyped(v: string | null | undefined): string {
  if (!v) return ''
  return `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(2, 4)}` + (v.length >= 16 ? ` ${v.slice(11, 16)}` : '')
}

/** The slashes go in as you type: 060120 reads 06/01/20. 6/1/20 and month names stay as typed. */
export function autoSlash(raw: string, prev: string, withTime: boolean): string {
  if (raw.length <= prev.length || !/^[\d/ :]*$/.test(raw)) return raw   // deleting, or a month name
  const g: string[] = ['']
  let time = ''
  let inTime = false
  for (const c of raw) {
    if (inTime) { if (/[\d:]/.test(c)) time += c; continue }
    if (c === ' ' || c === ':') { if (g.length === 3 && g[2]) inTime = withTime; continue }
    if (c === '/') { if (g[g.length - 1] && g.length < 3) g.push(''); continue }
    const i = g.length - 1
    if (i === 2 && withTime && g[2].length >= 2) { inTime = true; time += c; continue }
    if (i === 2 && g[2].length >= 4) continue
    g[i] += c
    if (i < 2 && g[i].length === 2) g.push('')
  }
  const date = g.join('/')
  if (!inTime) return date
  if (time.includes(':')) return `${date} ${time.slice(0, 5)}`
  const hm = time.slice(0, 4)
  return `${date} ${hm.length > 2 ? `${hm.slice(0, 2)}:${hm.slice(2)}` : hm}`
}
