# MummyTKT's Bias Pointer — Project Instructions

## Git: commit and push after every change

After completing **any meaningful set of code changes** in this project, always:

1. Stage the modified files (never `.env`, `*.db*`, `*.log`, `__pycache__/`, `node_modules/`, `.next/`)
2. Commit with a clear message describing what changed and why
3. Push to `origin master` immediately

Do not wait to be asked. Every feature, fix, and tweak must be in GitHub before the session ends.
Use the `/git-sync` skill or follow its steps directly.

## Stack

- **Backend**: Python 3.11, FastAPI, APScheduler, SQLite (`forex_radar.db`)
- **Frontend**: Next.js 14 (App Router), TypeScript, SWR — lives in `frontend/`
- **Data**: Twelve Data API (Daily + H4 OHLCV)
- **Auth**: JWT (python-jose), PBKDF2-SHA256 passwords, token stored as `mbp_token` in localStorage
- **Deployment**: Fly.io (backend), Vercel (frontend planned)

## Key conventions

- All API routes are under `/api/` prefix; auth middleware gates them when a user account exists
- Datetimes are stored as ISO 8601 UTC strings in SQLite — never use SQLite date types
- Instrument symbols stored without slash internally (`EURUSD`), Twelve Data uses slash (`EUR/USD`)
- Frontend timezone is stored in localStorage as `mbp_tz`; all date display goes through `useTimezone().fmtDate`
- Auth-aware fetch helper must be used for all API calls from the frontend (`authFetch` / `apiFetch`)
