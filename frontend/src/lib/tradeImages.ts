const DB_NAME = 'mbp_trade_images'
const DB_VERSION = 1
const STORE = 'images'

export interface TradeImage {
  id: number
  tradeId: number
  type: 'before' | 'after'
  blob: Blob
  name: string
  addedAt: string
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true })
        store.createIndex('tradeId', 'tradeId', { unique: false })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

export async function getTradeImages(tradeId: number, type?: 'before' | 'after'): Promise<TradeImage[]> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly')
      const req = tx.objectStore(STORE).index('tradeId').getAll(tradeId)
      req.onsuccess = () => {
        const all = req.result as TradeImage[]
        resolve(type ? all.filter(r => r.type === type) : all)
      }
      req.onerror = () => reject(req.error)
    })
  } catch { return [] }
}

export async function addTradeImage(tradeId: number, type: 'before' | 'after', file: File): Promise<number> {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    const req = tx.objectStore(STORE).add({
      tradeId, type, blob: file, name: file.name,
      addedAt: new Date().toISOString(),
    })
    req.onsuccess = () => resolve(req.result as number)
    req.onerror = () => reject(req.error)
  })
}

export async function deleteTradeImage(id: number): Promise<void> {
  try {
    const db = await openDb()
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      const req = tx.objectStore(STORE).delete(id)
      req.onsuccess = () => resolve()
      req.onerror = () => reject(req.error)
    })
  } catch { /* ignore */ }
}

export async function deleteAllTradeImages(tradeId: number): Promise<void> {
  try {
    const images = await getTradeImages(tradeId)
    await Promise.all(images.map(img => deleteTradeImage(img.id)))
  } catch { /* ignore */ }
}
