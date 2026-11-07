// The journal book as a real PDF file, saved straight to the device with no print box. The book from diaryBook.ts is
// laid out page by page in a hidden frame, each page is photographed, and the photos become the PDF's pages. So it looks
// just like the printed book (emojis and handwriting included), though its words can't be selected.
import { bookHtml, BOOK_FONTS, type BookInput } from './diaryBook'

// A5 at the browser's 96 dots an inch
const W = 559, H = 794
const PAD_X = 53, PAD_TOP = 57, PAD_BOTTOM = 60
const AVAIL_W = W - PAD_X * 2, AVAIL_H = H - PAD_TOP - PAD_BOTTOM
const SHARPNESS = 2.5

const SHEET_CSS = `
  html, body { margin: 0 !important; background: #fff !important; width: ${W}px; }
  .bar { display: none !important; }
  .cover { width: ${W}px !important; height: ${H}px !important; margin: 0 !important; box-shadow: none !important; }
  .sheet { position: relative; width: ${W}px; height: ${H}px; padding: ${PAD_TOP}px ${PAD_X}px 0; background: #fff; overflow: hidden; box-sizing: border-box; }
  .sheet .body { height: ${AVAIL_H}px; overflow: hidden; }
  .sheet .foot { position: absolute; left: 0; right: 0; bottom: 22px; text-align: center; font-size: 12px; color: #8a8496; }
  .sheet img { display: block; margin: 0 auto 10px; border-radius: 6px; max-height: none; background: none; }
  .sheet .noteline { margin: 0; padding: 0 0 0 15px; border-left: 3px solid var(--note); font-style: italic; white-space: pre-wrap; }
  .sheet .noteend { margin-bottom: 15px; }
  .sheet table { table-layout: fixed; }
  .sheet td.n { width: 42px; white-space: normal; }
  .sheet td:nth-child(2) { width: 33%; }
  .sheet td:nth-child(3) { width: 31%; }
  .sheet td.r { white-space: normal; }
`

const loaded = (img: HTMLImageElement) => img.complete ? Promise.resolve() : new Promise<void>(ok => { img.onload = () => ok(); img.onerror = () => ok() })
const nextPaint = () => new Promise(ok => setTimeout(ok, 0))
const FONTS = ["700 20px 'Dancing Script'", '500 14px Quicksand', '600 14px Quicksand', '700 14px Quicksand']
const fontsIn = (doc: Document) => Promise.race([
  Promise.all(FONTS.map(f => doc.fonts.load(f, 'Dear diary 2020 😊'))).catch(() => null),
  new Promise(ok => setTimeout(ok, 5000)),
])
// The photos are drawn on a canvas of the main page, so the fonts must be loaded there as well as in the frame,
// or the words come out in another font with their spaces in the wrong places
async function addFontsToPage(): Promise<HTMLLinkElement> {
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = BOOK_FONTS
  await new Promise<void>(ok => { link.onload = () => ok(); link.onerror = () => ok(); document.head.appendChild(link) })
  await fontsIn(document)
  return link
}

// The pieces of a page, in reading order, each small enough to move as one
function piecesOf(section: Element, doc: Document): HTMLElement[] {
  const out: HTMLElement[] = []
  for (const el of Array.from(section.children) as HTMLElement[]) {
    if (el.classList.contains('pics')) {
      for (const p of Array.from(el.children) as HTMLElement[]) {
        if (p instanceof doc.defaultView!.HTMLImageElement) {
          const r = p.naturalWidth ? p.naturalHeight / p.naturalWidth : 0.6
          const w = Math.min(AVAIL_W, Math.min(453, AVAIL_H) / r)
          p.style.width = `${Math.round(w)}px`
          p.style.height = `${Math.round(w * r)}px`
        }
        out.push(p)
      }
    } else if (el.classList.contains('note')) {
      // Line by line, so a long note can carry on to the next page
      const lines = (el.textContent || '').split('\n')
      lines.forEach((line, i) => {
        const d = doc.createElement('div')
        d.className = `noteline${i === lines.length - 1 ? ' noteend' : ''}`
        d.textContent = line || ' '
        out.push(d)
      })
    } else if (el.tagName === 'TABLE') {
      // A row each, so a long month's list can carry on too
      for (const tr of Array.from(el.querySelectorAll('tr'))) {
        const t = doc.createElement('table')
        t.appendChild(tr)
        out.push(t)
      }
    } else {
      out.push(el)
    }
  }
  return out
}

function layOut(doc: Document, onPage: (sheet: HTMLElement) => void) {
  let n = 1   // the cover is page 1
  const startSheet = () => {
    const sheet = doc.createElement('div')
    sheet.className = 'sheet'
    const body = doc.createElement('div')
    body.className = 'body'
    sheet.appendChild(body)
    doc.body.appendChild(sheet)
    return { sheet, body }
  }
  const finish = (s: { sheet: HTMLElement }) => {
    n += 1
    const foot = doc.createElement('div')
    foot.className = 'foot'
    foot.textContent = String(n)
    s.sheet.appendChild(foot)
    s.sheet.remove()   // only one page stays in the frame at a time, so each photo stays quick
    onPage(s.sheet)
  }
  const sections = Array.from(doc.querySelectorAll('.chapter, .page'))
  for (const section of sections) {
    const pieces = piecesOf(section, doc)
    section.remove()
    let cur = startSheet()
    for (const piece of pieces) {
      cur.body.appendChild(piece)
      if (cur.body.scrollHeight <= AVAIL_H) continue
      piece.remove()
      if (cur.body.childElementCount) { finish(cur); cur = startSheet() }
      cur.body.appendChild(piece)
      // Still too tall on an empty page: a very long paragraph, so it runs on word by word
      if (cur.body.scrollHeight > AVAIL_H && piece.childElementCount === 0) {
        const words = (piece.textContent || '').split(' ')
        let el = piece
        el.textContent = ''
        for (const word of words) {
          const before = el.textContent || ''
          el.textContent = before ? `${before} ${word}` : word
          if (before && cur.body.scrollHeight > AVAIL_H) {
            el.textContent = before
            const next = el.cloneNode(false) as HTMLElement
            finish(cur)
            cur = startSheet()
            next.textContent = word
            cur.body.appendChild(next)
            el = next
          }
        }
      }
    }
    finish(cur)
  }
}

export async function downloadBookPdf(book: BookInput, fileName: string, onProgress: (done: number, total: number) => void) {
  const [{ jsPDF }, { default: html2canvas }] = await Promise.all([import('jspdf'), import('html2canvas')])
  const frame = document.createElement('iframe')
  frame.setAttribute('aria-hidden', 'true')
  frame.style.cssText = `position:fixed;left:-20000px;top:0;width:${W}px;height:${H}px;border:0`
  document.body.appendChild(frame)
  let fontLink: HTMLLinkElement | null = null
  try {
    fontLink = await addFontsToPage()
    await new Promise<void>(ok => { frame.onload = () => ok(); frame.srcdoc = bookHtml(book) })
    const doc = frame.contentDocument!
    const css = doc.createElement('style')
    css.textContent = SHEET_CSS.replace('var(--note)', book.accentSoft)
    doc.head.appendChild(css)
    await Promise.all(Array.from(doc.images).map(loaded))
    await fontsIn(doc)

    const cover = doc.querySelector('.cover') as HTMLElement
    const sheets: HTMLElement[] = []
    cover.remove()
    layOut(doc, s => sheets.push(s))

    const pdf = new jsPDF({ unit: 'mm', format: 'a5', orientation: 'portrait', compress: true })
    pdf.setProperties({ title: book.title, author: book.owner })
    const pages = [cover, ...sheets]
    for (let i = 0; i < pages.length; i++) {
      onProgress(i + 1, pages.length)
      await nextPaint()
      doc.body.appendChild(pages[i])
      const canvas = await html2canvas(pages[i], {
        scale: SHARPNESS, backgroundColor: '#ffffff', logging: false, width: W, height: H, windowWidth: W, windowHeight: H,
      })
      pages[i].remove()
      if (i > 0) pdf.addPage('a5', 'portrait')
      pdf.addImage(canvas.toDataURL('image/jpeg', 0.9), 'JPEG', 0, 0, 148, 210, undefined, 'FAST')
      canvas.width = canvas.height = 0   // let the memory go before the next page
    }
    pdf.save(fileName)
  } finally {
    frame.remove()
    fontLink?.remove()
  }
}
