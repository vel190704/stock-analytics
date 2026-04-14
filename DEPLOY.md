# Deploy Guide

This guide covers local validation, GitHub push, and dashboard deployment.

## 1. Local Validation

```bash
cd ~/project/stock_market
make up
# wait for core services to be healthy
make seed

curl http://localhost:8000/health
curl http://localhost:8000/stocks
```

If `/stocks` is empty, allow ingestion loop to run for a short interval and retry.

## 2. Dashboard Local Run

```bash
cd ~/project/stock_market/dashboard
cp .env.example .env
# ensure backend URL points at local API
# VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

## 3. Push to GitHub

```bash
cd ~/project/stock_market
git init
git add .
git commit -m "feat: stock analytics pipeline v2"
gh repo create stock-analytics --public --push
```

Notes:

1. Make sure `gh auth login` was completed before creating the repo.
2. `.env` files are ignored by `.gitignore` and should not be committed.

## 4. Deploy Dashboard to Vercel

```bash
cd ~/project/stock_market/dashboard
vercel --prod
```

Set environment variables in Vercel project settings:

1. `VITE_API_URL`
2. `VITE_WS_URL`

## 5. Post-Deploy Checks

1. Open deployed dashboard and verify `/`, `/portfolio`, `/alerts`, `/backtest` pages load.
2. Verify authentication flow works (register/login/logout).
3. Confirm websocket feed updates ticker tape.
4. Confirm backend health endpoint and metrics endpoint are reachable from deployment target.
