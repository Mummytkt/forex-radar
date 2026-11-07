// A journal as a book the browser can save as a PDF: a cover, a chapter for each month, and one diary page per trade,
// oldest first. This file only builds the page; it takes the words already written by diaryStory.ts, so the book
// and the diary page on the site always read the same.
import type { Story } from './diaryStory'

export interface BookPicture { src: string | null }   // null: the picture could not be loaded
export interface BookRow { text: string; pictures: BookPicture[] }
export interface BookPage {
  monthNum: number
  yearNum: number
  monthWord: string      // "February"
  year: string
  dayLabel: string       // "Wed 5 Feb 2020"
  pair: string
  direction: 'buy' | 'sell'
  note: string
  story: Story
  topPictures: BookPicture[]    // pictures on the trade itself
  rows: BookRow[]
  otherPictures: BookPicture[]  // pictures on a row with no result ticked
  resultWord: string     // the month's list: "Win +3.00R"
}
export interface BookChapter { title: string; summary: string; pages: BookPage[] }
export interface BookInput {
  title: string          // "My H1 Entry Backtest Diary"
  owner: string
  span: string           // "January to February 2020"
  stats: string          // "13 pages · 6 wins"
  filterNote: string     // "" or "EURUSD only"
  accent: string
  accentSoft: string
  chapters: BookChapter[]
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const MOOD: Record<string, string> = { win: '#1F9D6B', loss: '#C9626B', be: '#C08A2E', out: '#7A7A95', open: '#7A7A95' }

const pics = (list: BookPicture[]) => list.length
  ? `<div class="pics">${list.map(p => p.src
    ? `<img src="${p.src}" alt="Chart">`
    : '<div class="nopic">This picture could not be loaded.</div>').join('')}</div>`
  : ''

function page(p: BookPage): string {
  const s = p.story
  return `<section class="page">
  <div class="head">
    <span class="ribbon" style="color:${MOOD[s.mood] || MOOD.open}">${esc(s.ribbon)}</span>
    <span class="stamp">${esc(p.monthWord)} trade ${p.monthNum} · ${esc(p.year)} trade ${p.yearNum}<br>${esc(p.dayLabel)}</span>
  </div>
  <div class="script greet">${esc(s.greeting)}</div>
  <p>${esc(s.opening)}${s.noNote ? ` ${esc(s.noNote)}` : ''}</p>
  ${p.note ? `<div class="note">${esc(p.note)}</div>` : ''}
  ${pics(p.topPictures)}
  ${p.rows.map(r => `<p>${esc(r.text)}</p>${pics(r.pictures)}`).join('\n  ')}
  ${pics(p.otherPictures)}
  ${s.held ? `<p>${esc(s.held)}</p>` : ''}
  <div class="sign">
    <div class="yours">${esc(s.yours)}</div>
    <div class="script name">${esc(s.signature)}</div>
  </div>
</section>`
}

function chapter(c: BookChapter): string {
  return `<section class="chapter">
  <div class="script ctitle">${esc(c.title)}</div>
  <div class="csum">${esc(c.summary)}</div>
  <table>
    ${c.pages.map(p => `<tr><td class="n">${p.monthNum}</td><td>${esc(p.dayLabel)}</td><td><b>${esc(p.pair)}</b> ${p.direction.toUpperCase()}</td><td class="r">${esc(p.resultWord)}</td></tr>`).join('\n    ')}
  </table>
</section>
${c.pages.map(page).join('\n')}`
}

export function bookHtml(b: BookInput): string {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>${esc(b.title)} - ${esc(b.owner)}</title>
<link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600;700&family=Quicksand:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  @page { size: A5; margin: 15mm 14mm 16mm; @bottom-center { content: counter(page); font: 9pt Quicksand, sans-serif; color: #8a8496; } }
  @page :first { margin: 0; @bottom-center { content: none; } }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  html, body { margin: 0; padding: 0; background: #fff; }
  body { font: 500 10.5pt/1.75 Quicksand, 'Segoe UI', sans-serif; color: #2f2a3a; }
  .script { font-family: 'Dancing Script', cursive; font-weight: 700; color: ${b.accent}; }
  p { margin: 0 0 3.5mm; }
  .cover { break-after: page; height: 210mm; padding: 20mm 15mm; display: flex; flex-direction: column; justify-content: center; text-align: center;
    background: linear-gradient(160deg, ${b.accentSoft}, #fff 75%); }
  .cover .title { font-size: 33pt; line-height: 1.2; margin-bottom: 7mm; }
  .cover .by { font-size: 12pt; font-weight: 600; }
  .cover .small { font-size: 9.5pt; color: #6d6680; margin-top: 2mm; }
  .chapter { break-before: page; }
  .ctitle { font-size: 28pt; line-height: 1.2; margin: 6mm 0 2mm; }
  .csum { font-size: 9.5pt; color: #6d6680; margin-bottom: 6mm; }
  table { width: 100%; border-collapse: collapse; font-size: 8.5pt; line-height: 1.4; }
  tr { break-inside: avoid; }
  td { padding: 1.6mm 1mm; border-bottom: 0.5pt solid #e7e2ee; vertical-align: top; }
  td.n { color: #8a8496; width: 6mm; }
  td.r { text-align: right; white-space: nowrap; font-weight: 600; }
  .page { break-before: page; }
  .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 4mm; margin-bottom: 3mm; }
  .ribbon { font-size: 9pt; font-weight: 700; }
  .stamp { font-size: 8.5pt; line-height: 1.45; color: #8a8496; text-align: right; }
  .greet { font-size: 21pt; line-height: 1.2; margin-bottom: 3mm; }
  .note { margin: 0 0 4mm; padding: 0.5mm 0 0.5mm 4mm; border-left: 0.7mm solid ${b.accentSoft}; font-style: italic; white-space: pre-wrap; }
  .pics { margin: 0 0 4mm; }
  .pics img { display: block; width: 100%; max-height: 120mm; object-fit: contain; margin-bottom: 2.5mm; border-radius: 1.5mm; break-inside: avoid; background: #111; }
  .nopic { font-size: 9pt; color: #8a8496; font-style: italic; }
  .sign { margin-top: 5mm; break-inside: avoid; }
  .yours { font-size: 9.5pt; color: #6d6680; line-height: 1.3; }
  .name { font-size: 20pt; line-height: 1.25; }
  .bar { position: sticky; top: 0; display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #2b1a47; color: #fff; font: 600 13px 'Segoe UI', sans-serif; z-index: 5; }
  .bar button { padding: 7px 14px; border: 0; border-radius: 7px; background: ${b.accent}; color: #fff; font: inherit; cursor: pointer; }
  @media screen {
    body { background: #ece9f2; }
    .cover, .chapter, .page { width: min(148mm, 100%); margin: 16px auto; background-color: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.14); }
    .chapter, .page { padding: 15mm 14mm; }
  }
  @media screen and (max-width: 600px) { .chapter, .page { padding: 20px 16px; } }
  @media print { .bar { display: none; } }
</style></head><body>
<div class="bar"><button onclick="window.print()">Save as PDF</button><span>In the box that opens, choose "Save as PDF" as the destination.</span></div>
<section class="cover">
  <div class="script title">${esc(b.title)}</div>
  <div class="by">${esc(b.owner)}</div>
  <div class="small">${esc(b.span)}</div>
  <div class="small">${esc(b.stats)}</div>
  ${b.filterNote ? `<div class="small">${esc(b.filterNote)}</div>` : ''}
</section>
${b.chapters.map(chapter).join('\n')}
</body></html>`
}

// Shown in the new tab while the pictures are being fetched
export const BOOK_WAIT = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Preparing your book</title></head>
<body style="font:600 15px 'Segoe UI',sans-serif;color:#3E1F5C;background:#f6f2fb;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">Preparing your book, gathering the pictures…</body></html>`
