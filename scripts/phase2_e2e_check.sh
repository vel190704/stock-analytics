#!/usr/bin/env bash
set -euo pipefail

echo "HEALTH"
curl -sS http://localhost:8000/health

echo "\nSTOCK_COUNT"
curl -sS http://localhost:8000/stocks | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("total"), len(d.get("data",[])))'

EMAIL="e2e_$(date +%s)@example.com"
PASS='StrongPass123!'
TOKEN=$(curl -sS -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')
echo "TOKEN_LEN ${#TOKEN}"

echo "CREATE_ALERT"
ALERT_STATUS=$(curl -sS -o /tmp/create_alert.json -w '%{http_code}' -X POST http://localhost:8000/alerts/rules -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"ticker":"AAPL","condition":"above","threshold":1,"user_email":"alerts@example.com"}')
echo "$ALERT_STATUS"
python3 -c 'import json;print(json.load(open("/tmp/create_alert.json"))["ticker"])'

echo "ADD_POSITION"
POS_STATUS=$(curl -sS -o /tmp/add_pos.json -w '%{http_code}' -X POST http://localhost:8000/portfolio/positions -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"ticker":"AAPL","quantity":5,"cost_basis":150}')
echo "$POS_STATUS"
python3 -c 'import json;d=json.load(open("/tmp/add_pos.json"));print(d["ticker"], d["quantity"])'

echo "ADD_TRADE"
TRADE_STATUS=$(curl -sS -o /tmp/add_trade.json -w '%{http_code}' -X POST http://localhost:8000/portfolio/trades -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"ticker":"AAPL","action":"BUY","quantity":1,"price":180}')
echo "$TRADE_STATUS"
python3 -c 'import json;d=json.load(open("/tmp/add_trade.json"));print(d["action"], d["ticker"])'

echo "BACKTEST_RUN"
BACKTEST_STATUS=$(curl -sS -o /tmp/backtest.json -w '%{http_code}' -X POST http://localhost:8000/backtest/run -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"ticker":"AAPL","strategy":"ma_crossover","params":{"fast_window":5,"slow_window":10},"start_date":"2026-03-01T00:00:00Z","end_date":"2026-04-13T23:59:59Z","initial_capital":10000}')
echo "$BACKTEST_STATUS"
python3 -c 'import json;d=json.load(open("/tmp/backtest.json"));print(d.get("ticker"), d.get("total_trades"), round(float(d.get("total_return_pct",0)),2))'

echo "SENTIMENT_REFRESH"
SENT_STATUS=$(curl -sS -o /tmp/sent_refresh.json -w '%{http_code}' -X POST http://localhost:8000/sentiment/AAPL/refresh)
echo "$SENT_STATUS"
cat /tmp/sent_refresh.json

echo "\nALERT_HISTORY_COUNT"
curl -sS http://localhost:8000/alerts/history | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d))'

echo "DASHBOARD_HTTP"
curl -sS -I http://localhost:3001 | head -n 1
