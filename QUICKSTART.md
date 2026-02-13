# Quick Start Guide

## Prerequisites

- Python 3.12+
- Node.js (for npm)
- `uv` (Python package manager)

## 1. Backend (FastAPI — port 8000)

```bash
cd backend

# Create .env from example and fill in your values
cp .env.example .env
# Edit .env with your DATABASE_URL, ANTHROPIC_API_KEY, etc.

# Install dependencies
uv sync

# Start the server
uv run uvicorn app.main:app --reload
```

Backend: **http://127.0.0.1:8000**
API docs: **http://127.0.0.1:8000/docs**

## 2. Frontend (React + Vite — port 5173)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend: **http://localhost:5173**

## 3. Environment Variables (backend `.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `ANTHROPIC_API_KEY` | For AI message generation |
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | Optional — can use cookies instead |
| `SECRET_KEY` | Any random string |

## 4. Health Check

Once both are running, visit http://127.0.0.1:8000/health — you should see `{"status": "healthy"}`.
