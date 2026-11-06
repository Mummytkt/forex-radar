// Turns a journal trade into a page of the diary. It only ever says what was entered:
// the words vary from page to page (by trade id, so a page always reads the same) but no fact is made up.

export interface StoryRow {
  slot: string
  label: string
  outcome: 'win' | 'loss' | 'be' | 'none'
  rr?: number | null
  takes?: number
  exit?: string
  net: number | null   // the entry's overall R, stop-outs included
}
export interface StoryInput {
  id: number
  name?: string
  date: string         // YYYY-MM-DD
  pair: string
  direction: 'buy' | 'sell'
  journal?: string
  exitDate?: string | null
  rows: StoryRow[]
}
export interface Story {
  greeting: string
  opening: string
  rows: { slot: string; label: string; text: string }[]
  closing: string
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const asDate = (d: string) => new Date(Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)))
export function longDate(d: string, withDay = true): string {
  const x = asDate(d)
  const main = `${MONTHS[x.getUTCMonth()]} ${x.getUTCDate()}, ${x.getUTCFullYear()}`
  return withDay ? `${DAYS[x.getUTCDay()]}, ${main}` : main
}
const R = (r: number) => `${r > 0 ? '+' : ''}${r.toFixed(2)}R`
const pick = (id: number, salt: number, list: string[]) => list[Math.abs(id * 7 + salt * 13) % list.length]
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`

function rowText(r: StoryRow, id: number, i: number): string {
  const takes = r.takes ?? 1
  const stops = takes - 1
  const run = stops > 0 ? `It took ${plural(takes, 'trade')}: ${plural(stops, 'stop-out')} first, then ` : ''
  let t: string
  if (r.outcome === 'win') {
    if (r.rr == null) t = stops > 0 ? `${run}the win. The RR isn't in yet.` : 'A win, though the RR isn\'t in yet.'
    else if (stops > 0) t = `${run}the win at 1:${r.rr}. Overall, ${R(r.net ?? 0)}.`
    else t = pick(id, i, [`It worked. Price paid you 1:${r.rr}, and that's ${R(r.net ?? 0)}.`, `A win at 1:${r.rr}, ${R(r.net ?? 0)} on the page.`, `This one delivered: 1:${r.rr}, ${R(r.net ?? 0)}.`])
  } else if (r.outcome === 'loss') {
    if (stops > 0) t = `${run}a loss. Overall, ${R(r.net ?? 0)}.`
    else t = pick(id, i, [`The stop was hit, ${R(r.net ?? 0)}.`, `This one didn't go your way: ${R(r.net ?? 0)}.`, `Price took the stop, ${R(r.net ?? 0)}.`])
  } else if (r.outcome === 'be') {
    const how = r.rr ? `you closed it at ${R(r.rr)}` : 'it came back to break even'
    t = stops > 0 ? `${run}${how}. Overall, ${R(r.net ?? 0)}.` : `No harm done: ${how}.`
  } else {
    t = pick(id, i, ['There was no entry here, and you stayed out.', 'No entry on this one. You kept your hands off.'])
  }
  if (r.exit && r.exit.length >= 16) t += ` You closed it on ${longDate(r.exit.slice(0, 10), false)} at ${r.exit.slice(11, 16)}.`
  return t
}

export function buildStory(s: StoryInput): Story {
  const name = s.name?.trim()
  const date = longDate(s.date)
  const verb = s.direction === 'buy' ? 'bought' : 'sold'
  const side = s.direction
  let opening = pick(s.id, 1, [
    `On ${date}, you ${verb} ${s.pair}.`,
    `${date} was the day you took a ${side} on ${s.pair}.`,
    `It was ${date}, and you ${verb} ${s.pair}.`,
  ])
  if (s.journal) opening += ` This page belongs to your ${s.journal} journal.`
  if (s.exitDate) {
    const days = Math.round((asDate(s.exitDate).getTime() - asDate(s.date).getTime()) / 86400000)
    opening += days <= 0 ? ' You closed it the same day.' : ` You held it for ${plural(days, 'day')}, until ${longDate(s.exitDate, false)}.`
  }
  const taken = s.rows.filter(r => r.outcome !== 'none')
  const nets = s.rows.map(r => r.net).filter((v): v is number => v != null)
  const best = nets.length ? Math.max(...nets) : null
  let closing: string
  if (!s.rows.length) closing = "You haven't written how it played out yet. Tap Edit when you're ready."
  else if (!taken.length) closing = pick(s.id, 2, ['No trade taken, and that is a decision too.', 'Sometimes the best trade is the one you leave alone.'])
  else if (best == null) closing = 'Add the RR when you can, and this page is complete.'
  else {
    const lead = nets.length > 1 ? `The best entry on this page made ${R(best)}.` : `This page closes at ${R(best)}.`
    closing = `${lead} ` + (best > 0
      ? pick(s.id, 3, ['Well played.', 'Patience paid.', 'One more golden page.'])
      : best < 0
        ? pick(s.id, 3, ['Every page makes you wiser.', 'A small price, and a lesson kept.', 'Turn the page and go again.'])
        : pick(s.id, 3, ['Capital protected.', 'Nothing lost, and something learned.']))
  }
  return {
    greeting: name ? `Hi ${name},` : 'Hi there,',
    opening,
    rows: s.rows.map((r, i) => ({ slot: r.slot, label: r.label, text: rowText(r, s.id, i + 4) })),
    closing,
  }
}
