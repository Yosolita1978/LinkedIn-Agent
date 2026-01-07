# LinkedIn Outreach Automation Agent

Automation agent for LinkedIn outreach to promote MujerTech courses.

## Project Structure
```
linkedin-outreach-agent/
├── backend/          # FastAPI + Playwright + LangGraph
│   ├── app/
│   │   ├── main.py       # FastAPI entry point
│   │   ├── config.py     # Environment configuration
│   │   ├── models/       # Database models
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # Business logic
│   │   └── utils/        # Helpers
│   └── tests/
├── frontend/         # React + Vite + Tailwind
└── .env.example      # Environment template
```

## Setup

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

## Tech Stack

- **Backend:** FastAPI, Playwright, LangGraph, SQLite
- **Frontend:** React, Vite, Tailwind CSS
- **AI:** Claude API (Anthropic)