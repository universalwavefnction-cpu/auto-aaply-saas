# Start Development Servers

Start both backend and frontend dev servers:

1. Backend: `cd ~/autoapply-web && uvicorn backend.main:app --reload --port 8000 &`
2. Frontend: `cd ~/autoapply-web/frontend && bun run dev &`
3. Report: Backend at http://localhost:8000, Frontend at http://localhost:5173
