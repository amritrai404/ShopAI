# ShopAI Deployment Guide

## Local Development

### Backend
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python scripts/seed_demo_data.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000