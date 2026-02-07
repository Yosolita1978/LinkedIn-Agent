# LinkedIn Intelligence & Outreach Agent

A personal intelligence tool for strategic LinkedIn outreach. It analyzes your LinkedIn connections, scores relationship warmth, detects outreach opportunities, generates personalized messages with AI, and prioritizes who to contact today.

Built for three use cases:

- **MujerTech** — Women entrepreneurs and tech professionals in Latin America
- **Cascadia AI** — AI/ML professionals in the Pacific Northwest
- **Job Search** — Strategic networking with people at target companies

## How It Works

```
LinkedIn Data Export (CSV)
        │
        ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Import &     │────▶│  Supabase    │◀────│  Segment     │
│ Parse        │     │  PostgreSQL  │     │  Contacts    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐    ┌──────────────┐
│   Score      │   │   Detect     │    │   Generate   │
│   Warmth     │   │   Outreach   │    │   Messages   │
│   (0-100)    │   │   Hooks      │    │   (OpenAI)   │
└──────────────┘   └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌──────────────┐
                   │   Rank &     │
                   │   Recommend  │
                   └──────────────┘
                            │
                            ▼
                   ┌──────────────┐
                   │   React      │
                   │   Dashboard  │
                   └──────────────┘
```

## Screenshots

The frontend is a dark-themed dashboard with 7 pages:

- **Dashboard** — Stats overview, warmth distribution, top recommendations
- **Today's Outreach** — Ranked contacts to reach out to, with reasons why
- **Contacts** — Searchable list with segment/warmth filters and pagination
- **Contact Detail** — Profile, warmth breakdown, message history, generate & queue
- **Queue** — Outreach pipeline: draft → approved → sent → responded
- **Opportunities** — Resurrection hooks (dormant, promises, unanswered, waiting)
- **Target Companies** — Manage job search target companies

## Features

### Warmth Scoring (0-100)

Every contact gets a warmth score based on 5 factors:

| Factor | Max | What It Measures |
|--------|-----|------------------|
| Recency | 30 | How recently you messaged (30 if < 7 days, 0 if > 180 days) |
| Frequency | 20 | Total message volume (20 if 20+ messages) |
| Depth | 25 | Average message length + substantive message ratio |
| Responsiveness | 15 | Balance of sent vs received messages |
| Initiation | 10 | Whether they initiate conversations |

### Audience Segmentation

Contacts are auto-tagged into segments based on their profile data:

- **MujerTech** — Matches LATAM locations + entrepreneurship/tech keywords
- **Cascadia AI** — Matches PNW locations or companies + AI/ML keywords
- **Job Target** — Matches companies in your target list

### Resurrection Scanner

Detects 4 types of outreach opportunities by analyzing message patterns:

| Hook Type | What It Finds |
|-----------|---------------|
| `they_waiting` | Their last message was to you — ball is in your court |
| `question_unanswered` | They asked a question you never answered |
| `promise_made` | You said "I'll..." or "let me..." but didn't follow up |
| `dormant` | Warm relationship (40+ warmth) gone quiet for 60+ days |

### Contact Ranking

Daily outreach recommendations ranked by a composite priority score:

```
priority = warmth (40%) + segment relevance (25%) + urgency (35%)
```

Each recommendation includes human-readable reasons like "They're waiting for your reply" or "Works at a target company."

### AI Message Generation

Generates personalized outreach messages using OpenAI (gpt-4o) with:

- Contact context (profile, company, headline)
- Message history summary
- Segment-appropriate tone
- Resurrection hooks as conversation openers
- Multiple variations to choose from
- 7 purpose templates (reconnect, introduce, follow up, invite, ask advice, congratulate, share resource)

### Outreach Queue

A managed pipeline for tracking message status:

```
draft → approved → sent → responded
```

Prevents duplicate outreach (one active item per contact). Auto-dismisses resurrection opportunities when a contact is queued.

## Tech Stack

**Backend:**
- Python 3.12+ / FastAPI / Uvicorn
- SQLAlchemy 2.0 (async ORM) + asyncpg
- Supabase PostgreSQL
- OpenAI Agents SDK (gpt-4o with built-in tracing)
- Playwright (browser automation for LinkedIn scraping)

**Frontend:**
- React 19 / TypeScript 5.9
- Vite 7
- Tailwind CSS 4 (dark theme)
- React Router 7

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- A [Supabase](https://supabase.com) project (free tier works)
- An [OpenAI API key](https://platform.openai.com)

### 1. Clone and set up the backend

```bash
cd backend
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt

# Start the server
uv run uvicorn app.main:app --reload
# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 2. Set up the frontend

```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

### 3. Import your LinkedIn data

1. Go to LinkedIn → Settings → Data Privacy → Get a copy of your data
2. Download your data export (you need `Connections.csv` and `messages.csv`)
3. Upload via the API or use the upload endpoints:

```bash
# Upload connections
curl -X POST http://localhost:8000/api/upload/connections \
  -F "file=@Connections.csv"

# Upload messages
curl -X POST http://localhost:8000/api/upload/messages \
  -F "file=@messages.csv"
```

### 4. Run the intelligence pipeline

```bash
# Calculate warmth scores for all contacts
curl -X POST http://localhost:8000/api/contacts/recalculate-warmth

# Run audience segmentation
curl -X POST http://localhost:8000/api/contacts/segment

# Scan for resurrection opportunities
curl -X POST http://localhost:8000/api/resurrection/scan
```

Then open the dashboard at `http://localhost:5173` and navigate to "Today's Outreach" for your ranked recommendations.

## Environment Variables

Create `backend/.env`:

```bash
# Database (Supabase PostgreSQL connection string)
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<host>:5432/postgres

# AI (OpenAI API key for message generation)
OPENAI_API_KEY=sk-...

# App
APP_ENV=development
```

## API Reference

The backend exposes 8 routers with 30+ endpoints. Full interactive docs available at `http://localhost:8000/docs` when running.

| Router | Prefix | Purpose |
|--------|--------|---------|
| Upload | `/api/upload/` | Import LinkedIn CSV exports |
| Contacts | `/api/contacts/` | CRUD, search, filter, warmth, segmentation |
| Target Companies | `/api/target-companies/` | Manage job search targets |
| Resurrection | `/api/resurrection/` | Scan and manage outreach opportunities |
| Generate | `/api/generate/` | AI message generation |
| Queue | `/api/queue/` | Outreach pipeline management |
| Ranking | `/api/ranking/` | Daily outreach recommendations |

## Project Structure

```
linkedin-outreach-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── models/              # 6 database models
│   │   ├── routes/              # 8 API routers
│   │   ├── services/            # Business logic
│   │   │   ├── export_parser.py
│   │   │   ├── warmth_scorer.py
│   │   │   ├── segmenter.py
│   │   │   ├── resurrection_scanner.py
│   │   │   ├── message_generator.py
│   │   │   ├── ranking_service.py
│   │   │   ├── queue_service.py
│   │   │   └── linkedin_browser.py
│   │   └── schemas/             # Pydantic validation
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/                 # Typed API client layer
│   │   ├── components/          # Shared UI components
│   │   ├── pages/               # 7 route pages
│   │   └── types/               # TypeScript interfaces
│   └── index.html
└── docs/
    ├── ARCHITECTURE.md          # System design
    ├── PROGRESS.md              # Build progress
    ├── DECISIONS.md             # Architecture decisions
    └── CHANGELOG.md             # Version history
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design, database schema, algorithm details
- [Progress](docs/PROGRESS.md) — What's been built and what's next
- [Decisions](docs/DECISIONS.md) — Architecture Decision Records
- [Changelog](docs/CHANGELOG.md) — Version history
- [Scraping Series](docs/scraping-series/) — 7-part tutorial on LinkedIn scraping with Playwright

## License

Private project. Not for distribution.
