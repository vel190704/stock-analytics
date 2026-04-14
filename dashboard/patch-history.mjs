import { readFileSync, writeFileSync } from 'fs'

let content = readFileSync('mock-server.mjs', 'utf8')

const oldHistory = `const makeHistory = (ticker) =>
  Array.from({ length: 60 }, (_, i) => {
    const base = bases[ticker]
    const open = generatePrice(base)
    const close = generatePrice(base)
    const t = new Date(Date.now() - (60 - i) * 60000)
    return {
      bucket: t.toISOString(), ticker,
      open: +open.toFixed(2), close: +close.toFixed(2),
      high: +(Math.max(open,close)*1.003).toFixed(2),
      low:  +(Math.min(open,close)*0.997).toFixed(2),
      volume: Math.floor(Math.random()*1000000+100000)
    }
  })`

const newHistory = `const makeHistory = (ticker) =>
  Array.from({ length: 60 }, (_, i) => {
    const base = bases[ticker] || 100
    const open = generatePrice(base)
    const close = generatePrice(base)
    const t = new Date(Date.now() - (60 - i) * 60000)
    return {
      bucket: t.toISOString(),
      event_time: t.toISOString(),
      ticker,
      open: +open.toFixed(2), close: +close.toFixed(2),
      high: +(Math.max(open,close)*1.003).toFixed(2),
      low:  +(Math.min(open,close)*0.997).toFixed(2),
      volume: Math.floor(Math.random()*1000000+100000),
      vwap: +((open+close)/2).toFixed(2),
      price_change: +(close-open).toFixed(2),
      pct_change: +((close-open)/open*100).toFixed(4)
    }
  })`

writeFileSync('mock-server.mjs', content.replace(oldHistory, newHistory))
console.log('Patched!')
