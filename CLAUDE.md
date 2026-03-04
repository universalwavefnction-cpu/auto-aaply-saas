# AutoApply Web

## Development Workflow

**Frontend: always use `bun`, not `npm`.** Backend uses `pip` + `ruff` + `pytest`.

```sh
# 1. Make changes

# 2. Backend lint (fast)
ruff check backend/

# 3. Frontend typecheck (fast)
cd frontend && bun run typecheck

# 4. Run tests
pytest tests/ -x -q                        # Backend
cd frontend && bun run test                 # Frontend

# 5. Lint before committing
ruff check backend/ && cd frontend && bun run lint

# 6. Before creating PR
# Run /verify to check everything
```

### Quick Reference
```bash
# Backend
uvicorn backend.main:app --reload --port 8000    # Dev server
ruff check backend/                                # Lint
ruff format backend/                               # Format
pytest tests/ -x -q                                # Test

# Frontend (from frontend/ dir)
bun run dev                                        # Dev server (port 5173)
bun run typecheck                                  # TypeScript check
bun run lint                                       # ESLint
bun run format                                     # Prettier
bun run test                                       # Vitest
bun run build                                      # Production build
```

### Slash Commands
- `/commit-push-pr` — Stage, commit, push, create PR
- `/verify` — Run all checks (lint + typecheck + tests, both stacks)
- `/deploy` — Build and deploy to EC2
- `/lint-file <path>` — Lint and fix a single file
- `/simplify <path>` — Simplify a file (remove dead code, redundancy)
- `/review` — Review uncommitted changes for issues
- `/dev` — Start both dev servers

## Key Conventions
- Run backend from project root: `uvicorn backend.main:app`
- Backend imports: `from backend.xxx import ...`
- API routes under `/api/` prefix
- All scrapers inherit `BaseScraper` from `backend/scrapers/base.py`
- Form filling uses fuzzy Q&A matching from user profile
- SQLite DB at `data/autoapply.db` — never commit
- Uploads at `data/uploads/` — never commit
- `bot_engine.py` is ~4500 lines — excluded from ruff lint, be careful with large edits

## Architecture
- **Backend**: Python FastAPI + SQLAlchemy + SQLite (port 8000)
- **Frontend**: React 18 + Vite + TypeScript + Tailwind (port 5173, proxies /api to 8000)
- **Automation**: Playwright headless browser
- **Workers**: Celery + Redis (scrape + apply cycles)
- **Deploy**: AWS EC2 at `ubuntu@52.30.96.169`

## Key Files
```
backend/
├── main.py              # FastAPI app + routes + /api/health
├── config.py            # Settings (env-based)
├── models.py            # SQLAlchemy models
├── database.py          # DB engine + session
├── auth.py              # JWT auth
├── bot_engine.py        # All platform logic (~4500 lines)
├── api/                 # Route modules (auth, profile, jobs, applications, dashboard, bot)
├── scrapers/            # Platform scrapers (stepstone, xing)
├── automation/          # Form filler (fuzzy Q&A matching)
└── workers/             # Celery tasks (scrape_worker, apply_worker)
frontend/src/
├── App.tsx              # Router + sidebar layout
├── api.ts               # API client
└── pages/               # Dashboard, Jobs, Applications, Profile, Settings, BotLive
```

## Database (SQLite)
- users, profiles, credentials, jobs, applications, job_filters
- See `backend/models.py` for full schema

## Platforms
- StepStone (working), Xing (working), Indeed (Cloudflare issues), LinkedIn (working)
- Xing has 20.9% success rate (best), StepStone 1.6% (worst)

## Anti-Detection
- Random delays, realistic UA, human-like typing speed
- Use blacklist to skip companies that already rejected
