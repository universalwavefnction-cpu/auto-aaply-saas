# AutoApply Web — Cloud Job Application Platform

## What This Is
Web-based job application automation platform. Successor to the desktop AutoApply app.
Runs on AWS EC2, accessible via browser, auto-applies to jobs across German platforms.

## Current State (Feb 25, 2026)
- **Phase**: Initial build — backend complete, frontend in progress
- **Origin data**: 1,873 applications migrated from desktop app (~/.autoapply/)
- **Platforms**: StepStone, Xing (LinkedIn planned)

## Architecture
- **Backend**: Python FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + Vite + Tailwind
- **Automation**: Playwright headless browser
- **Workers**: Background scrape + apply cycles
- **Deploy target**: AWS EC2 (existing: ubuntu@54.170.2.102)

## Key Files
```
autoapply-web/
├── backend/
│   ├── main.py              # FastAPI app + routes
│   ├── config.py             # Settings (env-based)
│   ├── models.py             # SQLAlchemy: User, Profile, Job, Application, JobFilter
│   ├── database.py           # DB engine + session
│   ├── auth.py               # JWT auth + password hashing
│   ├── api/
│   │   ├── auth.py           # Register/login/me
│   │   ├── profile.py        # Profile CRUD, Q&A, CV upload, credentials
│   │   ├── jobs.py           # Job search/filter, filter config
│   │   ├── applications.py   # Application tracking, manual apply
│   │   └── dashboard.py      # Stats/analytics
│   ├── scrapers/
│   │   ├── base.py           # BaseScraper (Playwright lifecycle)
│   │   ├── stepstone.py      # StepStone search + apply
│   │   └── xing.py           # Xing search + apply
│   ├── automation/
│   │   └── form_filler.py    # Smart form detection (fuzzy match Q&A)
│   └── workers/
│       ├── scrape_worker.py  # Background job discovery
│       └── apply_worker.py   # Background auto-apply
├── frontend/                  # React dashboard
├── migrate_from_desktop.py    # Import from ~/.autoapply/
├── requirements.txt
└── CLAUDE.md
```

## Database (SQLite → data/autoapply.db)
- **users**: id, email, password_hash
- **profiles**: personal info, salary, experience, questions_json (Q&A pairs)
- **credentials**: platform login (stepstone, xing, linkedin)
- **jobs**: scraped listings (title, company, location, url, salary range)
- **applications**: tracking (status, response_status, error_log)
- **job_filters**: search config, blacklists, autopilot toggle

## How It Works
1. User configures profile + Q&A pairs + platform credentials
2. Scrape worker discovers jobs matching filters
3. Jobs appear in dashboard for browsing
4. Autopilot mode: apply worker auto-fills forms using fuzzy Q&A matching
5. Manual mode: user clicks "Apply" on specific jobs, gets redirected

## Run Locally
```bash
cd ~/autoapply-web
pip install -r requirements.txt
python migrate_from_desktop.py  # Import old data
uvicorn backend.main:app --reload --port 8000
cd frontend && npm install && npm run dev  # Port 5173
```

## Lessons from Desktop App
- Xing has 20.9% success rate (best), StepStone 1.6% (worst)
- Fix Q&A inconsistencies before running (salary, experience, English C1)
- Use blacklist to skip companies that already rejected
- Anti-detection: random delays, realistic UA, human-like typing speed
