import express from 'express'
import cors from 'cors'

const app = express()
app.use(cors())
app.use(express.json())

const tickers = ['AAPL','MSFT','NVDA','TSLA','GOOGL','META','AMZN','JPM','V','NFLX']

const generatePrice = (base) => +(base + (Math.random() - 0.5) * base * 0.02).toFixed(2)

const bases = { AAPL:182, MSFT:415, NVDA:875, TSLA:245, GOOGL:178, META:520, AMZN:185, JPM:198, V:275, NFLX:635 }

const makeStock = (ticker) => {
  const open = bases[ticker]
  const close = generatePrice(open)
  const pct = +((close - open) / open * 100).toFixed(4)
  return {
    ticker, latest_price: close, pct_change: pct,
    price_change: +(close - open).toFixed(2),
    volume: Math.floor(Math.random() * 5000000 + 500000),
    event_time: new Date().toISOString(),
    open, close,
    high: +(close * 1.005).toFixed(2),
    low:  +(close * 0.995).toFixed(2),
  }
}

const stocks = tickers.map(makeStock)

// OHLCV history
const makeHistory = (ticker) =>
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
  })

app.get('/stocks', (req, res) => res.json(stocks))

app.get('/stocks/:ticker', (req, res) => res.json(makeHistory(req.params.ticker.toUpperCase())))

app.get('/stocks/:ticker/latest', (req, res) => res.json(makeStock(req.params.ticker.toUpperCase())))

app.get('/stocks/:ticker/stats', (req, res) => {
  const t = req.params.ticker.toUpperCase()
  const b = bases[t] || 100
  res.json({ ticker:t, min_price:+(b*0.97).toFixed(2), max_price:+(b*1.03).toFixed(2),
    avg_price:+b.toFixed(2), total_volume:15000000, event_count:360,
    start: new Date(Date.now()-86400000).toISOString(), end: new Date().toISOString() })
})

app.get('/analytics/top-gainers', (req, res) =>
  res.json([...stocks].sort((a,b) => b.pct_change - a.pct_change).slice(0,5)))

app.get('/analytics/top-losers', (req, res) =>
  res.json([...stocks].sort((a,b) => a.pct_change - b.pct_change).slice(0,5)))

app.get('/analytics/volume-leaders', (req, res) =>
  res.json([...stocks].sort((a,b) => b.volume - a.volume).slice(0,5)))

app.get('/analytics/moving-average/:ticker', (req, res) => {
  const t = req.params.ticker.toUpperCase()
  const b = bases[t] || 100
  res.json({ ticker:t, window:20,
    values: Array.from({length:20},(_,i)=>({
      event_time: new Date(Date.now()-i*60000).toISOString(),
      ma: generatePrice(b)
    }))
  })
})

app.get('/analytics/volatility/:ticker', (req, res) =>
  res.json({ ticker: req.params.ticker.toUpperCase(), volatility: +(Math.random()*2+0.5).toFixed(4) }))

app.get('/health', (req, res) =>
  res.json({ status:'ok', kafka:'ok', db:'ok', redis:'ok' }))

app.listen(8000, () => console.log('Mock API running on http://localhost:8000'))

import { WebSocketServer } from 'ws'
const wss = new WebSocketServer({ port: 8001 })
const tickers2 = ['AAPL','MSFT','NVDA','TSLA','GOOGL','META','AMZN','JPM','V','NFLX']
const bases2 = { AAPL:182,MSFT:415,NVDA:875,TSLA:245,GOOGL:178,META:520,AMZN:185,JPM:198,V:275,NFLX:635 }

wss.on('connection', (ws) => {
  console.log('WS client connected')
  const interval = setInterval(() => {
    const ticker = tickers2[Math.floor(Math.random()*tickers2.length)]
    const base = bases2[ticker]
    const close = +(base + (Math.random()-0.5)*base*0.01).toFixed(2)
    const open = +(base + (Math.random()-0.5)*base*0.005).toFixed(2)
    ws.send(JSON.stringify({
      ticker, close, open,
      high: +(close*1.002).toFixed(2),
      low: +(close*0.998).toFixed(2),
      volume: Math.floor(Math.random()*500000+50000),
      pct_change: +((close-open)/open*100).toFixed(4),
      price_change: +(close-open).toFixed(2),
      event_time: new Date().toISOString(),
      latest_price: close
    }))
  }, 1000)
  ws.on('close', () => clearInterval(interval))
})
console.log('WS server running on ws://localhost:8001')
