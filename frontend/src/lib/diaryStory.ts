// Turns a journal trade into a page of the owner's diary, written in the first person. The trade's facts come only
// from what was entered. The words around them change from page to page (chosen by trade id, so a page always reads
// the same), and they say nothing about the market that wasn't entered.

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
  hasNote: boolean
  exitDate?: string | null
  rows: StoryRow[]
}
export type Mood = 'win' | 'loss' | 'be' | 'out' | 'open'
export interface Story {
  greeting: string
  opening: string      // ends in ':' when the note follows
  noNote: string       // the words that stand in for the note ('' when there is one)
  rows: { slot: string; text: string }[]
  held: string
  yours: string
  signature: string
  mood: Mood
  ribbon: string
  sparks: string[]
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
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
// the same trade always gets the same words; neighbouring trades get different ones
const pick = (id: number, salt: number, list: string[]) => list[(Math.imul(id * 31 + salt * 1009 + 7, 2654435761) >>> 16) % list.length]
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

function rowText(r: StoryRow, id: number, i: number, many: boolean): string {
  const rr = `1:${r.rr}`
  const net = R(r.net ?? 0)
  const stops = (r.takes ?? 1) - 1
  const salt = 40 + i * 5
  let t: string
  if (r.outcome === 'win') {
    if (r.rr == null) t = stops > 0
      ? `it took me ${plural(stops + 1, 'trade')}: ${plural(stops, 'stop-out')}, then the win 💪 I still have to add the RR.`
      : pick(id, salt, ['the trade ended up a win 🎉 I still have to add the RR.', 'this one ended in a win 🌟 The RR is still to come.'])
    else if (stops > 0) t = pick(id, salt, [
      `it took me ${plural(stops + 1, 'trade')}: ${plural(stops, 'stop-out')} first, then the win at ${rr} 💪 Overall, ${net}.`,
      `I got stopped ${stops === 1 ? 'once' : `${stops} times`} and went again, and the win came at ${rr} 🌱 Overall, ${net}.`,
    ])
    else t = pick(id, salt, [
      `the trade ended up a win 🎉 Price paid me ${rr}, and that's ${net}.`,
      `this one ended in a beautiful win 🌟 ${rr}, ${net} on the page.`,
      `it went my way, all the way to ${rr} 💖 A ${net} win.`,
      `the trade ended up a win at ${rr} 🌸 ${net}, and I smiled.`,
      `patience paid me ${rr} on this one ✨ ${net} in the book.`,
      `I got my ${rr} 🎀 A clean win, ${net}.`,
    ])
  } else if (r.outcome === 'loss') {
    if (stops > 0) t = `it took ${plural(stops + 1, 'trade')}, and all of them hit the stop 🍃 Overall, ${net}. Lesson learnt.`
    else t = pick(id, salt, [
      `the trade ended in a loss 🍃 ${net}. Lesson learnt, and I'm moving on.`,
      `the stop was hit, ${net} 🌧️ Lesson learnt.`,
      `it didn't go my way this time 🍂 ${net}, and that is part of the journey.`,
      `the trade ended a loss, ${net} 🌱 I'm keeping the lesson.`,
      `price took my stop, ${net} 🕊️ I let it go, and I learn from it.`,
    ])
  } else if (r.outcome === 'be') {
    if (r.rr) t = (r.rr > 0
      ? pick(id, salt, [`I closed it early at ${R(r.rr)} 🌤️ A little kept is still kept.`, `I took ${R(r.rr)} off the table and closed it 🌼`])
      : pick(id, salt, [`I closed it early at ${R(r.rr)} 🌤️ A small cost, and my choice.`, `I stepped out early at ${R(r.rr)} 🍃 Better a small cut than a full stop.`]))
      + (stops > 0 ? ` Overall, ${net}.` : '')
    else t = pick(id, salt, [
      'the trade was a breakeven 🕊️ No harm done, and my capital is safe.',
      'it came back and closed at breakeven 🌤️ Nothing lost.',
      'it ended flat, a breakeven 🌿 I live to trade another day.',
    ]) + (stops > 0 ? ` With the stop-outs before it, ${net} overall.` : '')
  } else {
    t = pick(id, salt, [
      'there was no entry for me 🌙 I stayed out and kept my peace.',
      "no entry on this one 🌿 It wasn't there, so I left it alone.",
      "I didn't get in 🕊️ No entry, and no regrets.",
    ])
  }
  if (r.exit && r.exit.length >= 16) t += ` I closed it on ${longDate(r.exit.slice(0, 10), false)} at ${r.exit.slice(11, 16)} ⏰`
  return many ? `On ${r.label}, ${t}` : `${cap(t)}`
}

const RIBBON: Record<Mood, string> = { win: 'A winning page', loss: 'A lesson page', be: 'A calm page', out: 'A patient page', open: 'Still being written' }
const SPARKS: Record<Mood, string[]> = {
  win: ['✨', '🌟', '🌸', '🎉', '💖'],
  loss: ['🍃', '🌱', '🕊️', '🌅', '🍂'],
  be: ['🌤️', '🕊️', '🌿', '☁️', '🌼'],
  out: ['🌙', '⭐', '🌿', '🕊️', '✨'],
  open: ['✍️', '🌙', '✨', '🪶', '🌸'],
}

export function buildStory(s: StoryInput): Story {
  const date = longDate(s.date)
  const verb = s.direction === 'buy' ? 'bought' : 'sold'
  const side = s.direction
  const p = s.pair
  // every row ticked "no entry": the trade was only watched, so the page must not say it was taken
  const watched = s.rows.length > 0 && s.rows.every(r => r.outcome === 'none')
  const opening = watched
    ? pick(s.id, 1, s.hasNote
      ? [`On ${date}, I was watching ${p} for a ${side}, because of the following confluences:`, `On ${date}, ${p} had my attention for a ${side}. This is what I saw:`]
      : [`On ${date}, I was watching ${p} for a ${side}.`, `On ${date}, ${p} had my attention for a ${side}.`])
    : s.hasNote
    ? pick(s.id, 1, [
      `On ${date}, I ${verb} ${p} because of the following confluences:`,
      `On ${date}, I took a ${side} on ${p}, and here is why:`,
      `${date}. I ${verb} ${p}, and these were my confluences:`,
      `On ${date}, ${p} caught my eye and I ${verb} it. My reasons were these:`,
      `It was ${date} when I took a ${side} on ${p}. This is what I saw:`,
    ])
    : pick(s.id, 1, [
      `On ${date}, I ${verb} ${p}.`,
      `On ${date}, I took a ${side} on ${p}.`,
      `It was ${date}, and I ${verb} ${p}.`,
      `${date} was the day I took a ${side} on ${p}.`,
    ])
  const noNote = s.hasNote ? '' : watched
    ? pick(s.id, 2, ['My plan was ready, and I waited for my moment 🌙', 'I kept my eyes on it, and my hands still 🌿'])
    : pick(s.id, 2, [
    'I saw my setup, trusted my plan and took it 🌿',
    'The chart lined up with my plan, so I stepped in 🌸',
    'I waited for my level, and then I took my chance ✨',
    'My plan said go, so I went, calm and steady 🕊️',
    "I didn't chase. I let price come to me, then I acted 🦋",
    'It was right by my rules, so I pressed the button 💫',
  ])
  let held = ''
  if (s.exitDate) {
    const days = Math.round((asDate(s.exitDate).getTime() - asDate(s.date).getTime()) / 86400000)
    held = days <= 0
      ? pick(s.id, 3, ['I was in and out the same day ⏳', 'It was all done the same day ☀️', 'It opened and closed on the same day 🌤️'])
      : pick(s.id, 3, [`I held it for ${plural(days, 'day')}, until ${longDate(s.exitDate, false)} ⏳`, `I stayed with it for ${plural(days, 'day')} 🌙`, `It took ${plural(days, 'day')} from start to finish, closing on ${longDate(s.exitDate, false)} 🕰️`])
  }
  const taken = s.rows.filter(r => r.outcome !== 'none')
  const nets = taken.map(r => r.net).filter((v): v is number => v != null)
  const best = nets.length ? Math.max(...nets) : null
  // a win counts unless its stop-outs ate it; an early close in profit is calm, not a win
  const won = taken.some(r => r.outcome === 'win' && (r.net == null || r.net > 0))
  const mood: Mood = !s.rows.length ? 'open' : !taken.length ? 'out' : won ? 'win'
    : taken.some(r => r.outcome === 'be') || best == null || best === 0 ? 'be' : 'loss'
  return {
    greeting: pick(s.id, 4, ['Hi diary,', 'Dear diary,', 'Hello again, diary,', 'Hi diary,', 'Dear diary,']),
    opening,
    noNote,
    rows: s.rows.map((r, i) => ({ slot: r.slot, text: rowText(r, s.id, i, s.rows.length > 1) })),
    held,
    yours: pick(s.id, 6, ['Yours,', 'Yours,', 'Yours always,', 'Yours truly,']),
    signature: s.name?.trim() || 'Me',
    mood,
    ribbon: RIBBON[mood],
    sparks: SPARKS[mood],
  }
}
