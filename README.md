# ShopMate — Your AI Business Partner

Local-first AI business intelligence for small shops.
No paid LLM API keys required.

## Stack
FastAPI · PostgreSQL · scikit-learn · Ollama · FAISS · React + TS

## Quick start
1. Copy env: `cp .env.example .env`
2. Backend: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Frontend: `cd frontend && npm install`
4. Docker (optional): `docker compose -f infra/compose.yaml up --build`

## Status
- [x] Repo + folder structure
- [ ] CSV upload + cleaning
- [ ] PostgreSQL schema + Alembic
- [ ] Analytics engine
- [ ] ML forecasting
- [ ] Dual-mode chat (OpenRouter default + local App AI)
- [ ] RAG
- [ ] Full-stack UI
- [ ] Docker + CI
- [ ] AWS deploy