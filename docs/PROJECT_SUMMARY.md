# LinkedIn Intelligence & Outreach Agent — Project Summary

**Version:** 0.5.x
**Last updated:** June 23, 2026
**Status:** Core platform complete (Phases 1–5e). Follower engagement + campaign sequences in progress.

> This is the single consolidated overview of the project: what it does, how it's
> built, the key architecture decisions, and the current state. For deeper history
> see `ARCHITECTURE.md`, `DECISIONS.md`, `PROGRESS.md`, `CHANGELOG.md`, and
> `LINKEDIN-AUTOMATION-GAPS.md` in this same folder.

---

## 1. What It Is

A **personal intelligence tool for strategic LinkedIn outreach**. It imports your
LinkedIn data, scores how "warm" each relationship is, detects concrete reasons to
reach out, generates personalized messages with AI, and ranks who you should
contact today — all reviewed by a human before anything is sent.

It is built around three use cases:

1. **MujerTech** — Women entrepreneurs and tech professionals in Latin America
2. **Cascadia AI** — AI/ML professionals in the Pacific Northwest
3. **Job Search** — Strategic networking with people at target companies

The guiding principle is **human-in-the-loop**: the system suggests and drafts,
the user approves and sends.

---

## 2. High-Level Flow

```
LinkedIn Data Export (CSV)  +  Live LinkedIn (cookies)
            │
            ▼
   ┌──────────────────┐
   │ Import & Parse    │  export_parser
   └──────────────────┘
            │
            ▼
   ┌──────────────────┐
   │ Supabase Postgres │  (7 tables, SQLAlchemy async)
   └──────────────────┘
            │
   ┌────────┼─────────────────┬──────────────────┐
   ▼        ▼                 ▼                  ▼
 Warmth   Segmenter      Resurrection        Voyager / Playwright
 Scorer                  Scanner             enrichment + inbox sync
   │        │                 │                  │
   └────────┴────────┬────────┴──────────────────┘
                     ▼
            ┌──────────────────┐
            │ Ranking Service   │  composite priority (0–100)
            └──────────────────┘
                     │
                     ▼
            ┌──────────────────┐
            │ Message Generator │  OpenAI Agents SDK (gpt-4o)
            └──────────────────┘
                     │
                     ▼
            ┌──────────────────┐
            │ Outreach Queue    │  draft → approved → sent → responded
            └──────────────────┘
                     │
                     ▼
            ┌──────────────────┐
            │ React Dashboard   │  9 pages, dark theme
            └──────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, **FastAPI**, **SQLAlchemy (async)**, Pydantic / pydantic-settings |
| Database | **Supabase PostgreSQL** (async driver) |
| AI | **OpenAI Agents SDK** (`agents` package), model **`gpt-4o`** |
| Profile enrichment | **LinkedIn Voyager API** (fast path) → **Playwright** (fallback) |
| Inbox sync | **Playwright** (Voyager messaging API is dead — see §7) |
| Browser automation | **Playwright** (Python async) |
| Frontend | **React 19**, **TypeScript**, **Vite 7**, **Tailwind CSS 4**, **react-router-dom 7** |
| Showcase video | **Remotion v4** (`video/`) |

---

## 4. Backend Architecture

Location: `backend/app/`. FastAPI app with an async lifespan that initializes DB
tables on startup (`main.py`). CORS is currently restricted to the local frontend
(`localhost:5173` / `127.0.0.1:5173`).

### 4.1 Services (`app/services/`)

| Service | Purpose |
|---------|---------|
| `export_parser.py` | Parse LinkedIn CSV exports (Connections.csv, messages.csv) |
| `warmth_scorer.py` | Compute relationship warmth (0–100) from message patterns |
| `segmenter.py` | Auto-tag contacts into audience segments |
| `resurrection_scanner.py` | Detect outreach opportunities ("hooks") |
| `ranking_service.py` | Composite priority score → daily recommendations |
| `message_generator.py` | Generate personalized messages via OpenAI Agents SDK (gpt-4o) |
| `linkedin_voyager.py` | Fast profile enrichment via LinkedIn Voyager API |
| `linkedin_browser.py` | Playwright scraper (enrichment fallback, login, followers) |
| `follower_connector.py` | 3-phase follower → connection automation |
| `inbox_service.py` | Playwright-based inbox/message sync |
| `queue_service.py` | Outreach queue management (create/regenerate/status) |

### 4.2 API Routers (`app/routes/`)

| Router | Prefix | Purpose |
|--------|--------|---------|
| `upload` | `/api/upload` | CSV uploads + upload status |
| `contacts` | `/api/contacts` | Contact CRUD, filtering, stats, warmth recalc, segmentation |
| `target_companies` | `/api/target-companies` | Job-search target companies (single + bulk) |
| `resurrection` | `/api/resurrection` | Opportunity scans + dismiss |
| `generate` | `/api/generate` | AI message generation (single + batch) |
| `queue` | `/api/queue` | Outreach pipeline + per-item regenerate |
| `ranking` | `/api/ranking` | Daily ranked recommendations |
| `followers` | `/api/followers` | Scan → generate notes → connect → track → check acceptances |
| `analytics` | `/api/analytics` | Outreach analytics / stats |
| `auth` | `/api/auth` | LinkedIn session / cookie status |
| `inbox` | `/api/inbox` | Inbox sync (Playwright) |

### 4.3 Data Models (`app/models/` — 7 tables)

`contact`, `message`, `resurrection`, `target_company`, `queue` (OutreachQueueItem),
`upload` (DataUpload), and `connection_request` (follower-connection tracking).

Each model has a matching Pydantic schema in `app/schemas/`.

---

## 5. Core Algorithms

### 5.1 Warmth Scoring (0–100)

| Factor | Max | Logic |
|--------|-----|-------|
| Recency | 30 | Days since last message (30 if <7d, 0 if >180d) |
| Frequency | 20 | Total messages (20 if 20+ messages) |
| Depth | 25 | Average length + substantive-message ratio |
| Responsiveness | 15 | Balance of sent vs received (15 if balanced) |
| Initiation | 10 | Whether they initiate conversations |

A **substantive message** is 100+ characters and not a shallow pattern
(e.g. "thanks", "congrats", emoji-only).

### 5.2 Audience Segments

- **MujerTech** — LATAM location (50+ cities/countries) + entrepreneur keywords. Warm, supportive tone (Spanish OK).
- **Cascadia AI** — PNW location + AI/ML keywords. Professional, tech-savvy, community-focused.
- **Job Target** — Company matches the `target_companies` table. Curious about their work, not asking for referrals.

### 5.3 Resurrection Hooks

| Hook | Detection |
|------|-----------|
| `dormant` | Warmth ≥40 AND no messages in 60+ days |
| `promise_made` | Your message says "I'll / let me…" with no follow-up |
| `question_unanswered` | They asked "?" and you never replied |
| `they_waiting` | Their message was the last one (ball in your court) |

### 5.4 Ranking / Priority Score (0–100)

`ranking_service` blends three signals into a weighted composite and excludes
contacts already in the active queue:

- **Warmth (40%)** — relationship strength
- **Segment score** — segment + manual tag membership
- **Urgency score** — highest-urgency active resurrection hook

It returns ranked contacts with human-readable **reasons** ("they're waiting on
you", segment membership, warmth tier) for the *Today's Outreach* view.

### 5.5 Message Generation

`message_generator` uses the **OpenAI Agents SDK** (`Agent` + `Runner`, model
`gpt-4o`, tracing enabled). Inputs: contact profile, recent message history (last
~5), segment context, active hooks, persona config, and purpose. Output: one or
more message variations. Persona is configurable via env (`PERSONA_*`).

---

## 6. Frontend Architecture

Location: `frontend/`. React 19 + TypeScript + Vite 7 + Tailwind 4, routed with
react-router-dom 7. Dark-themed dashboard.

### Pages (`src/pages/`)

| Page | Purpose |
|------|---------|
| `DashboardPage` | Stats overview, warmth distribution, top recommendations |
| `RecommendationsPage` | Today's ranked outreach with reasons |
| `ContactsPage` | Searchable list with segment/warmth filters + pagination |
| `ContactDetailPage` | Profile, warmth breakdown, message history, generate & queue |
| `QueuePage` | Outreach pipeline: draft → approved → sent → responded |
| `OpportunitiesPage` | Resurrection hooks (dormant, promises, unanswered, waiting) |
| `TargetCompaniesPage` | Manage job-search target companies |
| `FollowersPage` | Follower → connection automation flow |
| `InboxPage` | Synced LinkedIn inbox |

- **Components** (`src/components/`): `Layout`, `LoadingSpinner`, `ErrorMessage`, `EmptyState`, and badges (`WarmthBadge`, `SegmentBadge`, `StatusBadge`, `PriorityBadge`).
- **API layer** (`src/api/`): one typed module per backend router, sharing a common `client.ts`.
- **Types** centralized in `src/types/index.ts`.

---

## 7. Key Architecture Decisions

These are the decisions that shape the system (full ADRs in `DECISIONS.md`):

1. **Cookie-based LinkedIn auth (ADR-001)** — Manual login once; session cookies
   (`li_at` + `JSESSIONID`) saved to `playwright-data/cookies.json` (gitignored).
   No stored username/password, avoids CAPTCHA/2FA automation.
2. **Playwright over Selenium (ADR-002)** — Async-native, auto-wait, modern API.
3. **Voyager API first, Playwright fallback** — Profile enrichment uses the fast
   Voyager JSON API; falls back to Playwright scraping when the API path fails.
4. **Encoded member IDs** — IDs like `ACoAAA…` must use `identity/dash/profiles`
   or `miniProfiles`, **not** `profileView`.
5. **Stable DOM selectors (ADR-003)** — LinkedIn uses hashed CSS classes, so the
   scraper relies on accessibility attributes (e.g. `figure[aria-label]`) and keeps
   multiple fallback selectors. `is_logged_in()` uses 7 fallback selectors + a
   URL-based fallback because the feed DOM changed.
6. **Scroll-based pagination (ADR-004)** — Infinite scroll handled with a max-items
   cap, "no new items" detection, and a hard scroll-attempt limit.
7. **Anti-detection (ADR-005)** — User-agent rotation, viewport randomization,
   randomized human-like delays and scrolling.
8. **Retry with exponential backoff + jitter (ADR-006)** and a **custom exception
   hierarchy (ADR-008)** (`LinkedInError` → `AuthenticationError` / `ScrapingError`).
9. **Voyager messaging API is dead (March 2026)** — `/messaging/conversations`
   returns 500; all alternative endpoints fail too. **Inbox sync therefore runs
   through Playwright**, scraping `linkedin.com/messaging/` (selector
   `li.msg-conversation-listitem`, matched by contact name; ~15–30s).
10. **Human-in-the-loop** — Every generated message and connection request is
    reviewed/approved by the user; rate limits cap daily messages/profiles.

---

## 8. Configuration

Backend settings (`app/config.py`, loaded from `backend/.env`):

```bash
# App
APP_ENV=development
SECRET_KEY=change-this-in-production

# Database (Supabase)
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# AI (OpenAI Agents SDK)
OPENAI_API_KEY=sk-...

# LinkedIn (for scraper / enrichment)
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your-password
LINKEDIN_PROFILE_URL=https://www.linkedin.com/in/you

# Persona (drives AI message tone)
PERSONA_NAME="Cristina Rodriguez"
PERSONA_TITLE="Tech Professional"
PERSONA_LOCATION="Seattle"
PERSONA_BIO=""
PERSONA_INTERESTS="AI, community building, Latin American tech"
PERSONA_TONE="warm, authentic, professional but friendly"

# Rate limits
RATE_LIMIT_MESSAGES_PER_DAY=50
RATE_LIMIT_PROFILES_PER_DAY=100
```

Frontend talks to the backend at `localhost` and is served by Vite on port 5173.

---

## 9. Phase Status

| Phase | Status |
|-------|--------|
| 1–4: Setup, Playwright, Intelligence, OpenAI + Queue | ✅ Done |
| 5: Frontend Dashboard (dark theme) | ✅ Done |
| 5b: Follower → connection automation (Voyager, 3-phase) | ✅ Done |
| 5c: Dashboard tooltips + Queue AI regeneration + Showcase video | ✅ Done |
| 5d: Quick fixes (notes, rate limits, persona config, cookie detection) | ✅ Done |
| 5e: Inbox sync (Playwright) | ✅ Done |
| Gap 1: Campaign sequences (multi-step follow-ups) | ⬜ Planned |
| Gap 9: Follower engagement strategy | 🔄 In progress |
| Phase 6: End-to-end testing | ⬜ Planned |
| Phase 7: Advanced features (content scheduling, search import, analytics) | ⬜ Planned |

---

## 10. Known Issues / Limitations

- **No Docker setup** — no Dockerfile / docker-compose.yml.
- **CORS is localhost-only** — only `localhost:5173` is allowed.
- **No real-time updates** — frontend fetches on page load; no polling/WebSocket/SSE.
- **LinkedIn DOM volatility** — scraping selectors break when LinkedIn updates; mitigated with multiple fallbacks.
- **Cookies expire** — Voyager/Playwright sessions need periodic re-login.
- **Voyager messaging API dead** — inbox sync depends on slower Playwright scraping.

---

## 11. Repository Map

```
linkedin-outreach-agent/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + router registration + lifespan
│   │   ├── config.py          # Pydantic settings (.env)
│   │   ├── database.py        # SQLAlchemy async engine/session
│   │   ├── models/            # 7 ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routes/            # 11 API routers
│   │   └── services/          # 11 domain services
│   ├── playwright-data/       # cookies.json (gitignored)
│   ├── tests/
│   ├── requirements.txt / pyproject.toml / uv.lock
│   └── README.md
├── frontend/
│   └── src/
│       ├── App.tsx, main.tsx
│       ├── pages/             # 9 dashboard pages
│       ├── components/        # Layout + shared UI + badges
│       ├── api/               # typed client per router
│       └── types/             # shared TS types
├── video/                     # Remotion v4 showcase (36s, 1920x1080)
├── docs/                      # ARCHITECTURE, DECISIONS, PROGRESS, CHANGELOG,
│                              #   LINKEDIN-AUTOMATION-GAPS, this summary
├── README.md
└── QUICKSTART.md
```

---

## 12. Where to Go Next

- **`ARCHITECTURE.md`** — original component/diagram reference (note: predates the OpenAI switch and the now-complete frontend).
- **`DECISIONS.md`** — full ADRs with code and trade-offs.
- **`PROGRESS.md`** — detailed build log and import results.
- **`LINKEDIN-AUTOMATION-GAPS.md`** — the gap analysis driving current work.
- **`CHANGELOG.md`** — release-by-release history.
```
