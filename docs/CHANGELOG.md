# Changelog

All notable changes to this project are documented here.

---

## [0.5.0] - 2026-02-06

### Phase 5: Frontend Dashboard

#### Added

- **Full React Dashboard** (5 pages, dark theme)
  - Dashboard: stat cards, warmth distribution bar, top 10 contacts, quick actions
  - Contacts: search, segment filter, sort by warmth/name/messages, pagination (30/page)
  - Contact Detail: profile, warmth breakdown bars (5 factors), message stats, resurrection opportunities, generate message + add to queue
  - Queue: status tabs (draft/approved/sent/responded), inline message editing, approve/send/delete workflow
  - Opportunities: hook type tabs, dismiss, generate & queue inline

- **Frontend Architecture**
  - React 19 + TypeScript 5.9 + Vite 7 + Tailwind CSS 4
  - react-router-dom with sidebar navigation (Layout component)
  - Typed API layer: `api/client.ts` (base fetch), `api/contacts.ts`, `api/queue.ts`, `api/resurrection.ts`, `api/generate.ts`
  - 7 shared components: WarmthBadge, SegmentBadge, StatusBadge, LoadingSpinner, ErrorMessage, EmptyState, Layout

- **Dark Theme UI**
  - slate-800/900 backgrounds, slate-200/400 text
  - Translucent colored badges (warmth: red/orange/blue/slate, segments: purple/teal/amber)
  - Blue accent for active states and primary actions

#### Fixed

- CORS: added `127.0.0.1:5173` origin alongside `localhost:5173`
- PostgreSQL ARRAY `.contains()`: switched from `sqlalchemy.ARRAY` to `sqlalchemy.dialects.postgresql.ARRAY`
- Database migration: added missing `purpose` and `approved_at` columns to `outreach_queue` table

---

## [0.4.0] - 2026-02-06

### Phase 4: OpenAI Migration + Queue Management

#### Changed

- **Message Generator — Switched from Anthropic to OpenAI Agents SDK**
  - Replaced `anthropic` package with `openai-agents`
  - Using `gpt-4o` model via Agent + Runner pattern
  - Built-in tracing enabled — view at https://platform.openai.com/traces
  - Removed `langchain` and `langgraph` dependencies (no longer needed)

#### Added

- **Outreach Queue Management** (`services/queue_service.py`, `routes/queue.py`)
  - 7 new API endpoints at `/api/queue/`
  - Status workflow: draft → approved → sent → responded
  - Duplicate prevention: one active item per contact
  - Queue statistics endpoint
  - Message editing for drafts
  - Delete protection for sent/responded items (kept for history)

- **Queue API Endpoints**
  - `POST /api/queue/` — Add message to queue as draft
  - `GET /api/queue/` — List items (filter by status, use_case)
  - `GET /api/queue/stats` — Queue statistics by status and use_case
  - `GET /api/queue/{id}` — Get single queue item
  - `PATCH /api/queue/{id}/status` — Transition status
  - `PATCH /api/queue/{id}/message` — Edit draft message
  - `DELETE /api/queue/{id}` — Remove draft/approved item

#### Note

- Queue endpoints will be fully tested via the React frontend (Phase 5)

---

## [0.3.0] - 2026-02-05

### Phase 3: Intelligence Engine Complete

Major milestone - the backend intelligence system is now fully functional.

#### Added

- **Database Schema (6 Tables)**
  - `contacts` - Core contact data with warmth scoring and segmentation
  - `messages` - Message history with direction and content analysis
  - `resurrection_opportunities` - Detected outreach hooks
  - `target_companies` - Job search target list
  - `outreach_queue_items` - Message queue (pending implementation)
  - `data_uploads` - Upload tracking

- **LinkedIn Export Parser** (`services/export_parser.py`)
  - Parse Connections.csv (2,333 contacts imported)
  - Parse messages.csv (5,823 messages imported)
  - Automatic direction detection (sent/received)
  - Sponsored message filtering
  - Contact creation from message data

- **Warmth Scoring Engine** (`services/warmth_scorer.py`)
  - 5-factor scoring algorithm (0-100 points)
  - Recency (30pts), Frequency (20pts), Depth (25pts)
  - Responsiveness (15pts), Initiation (10pts)
  - Substantive message detection

- **Audience Segmentation** (`services/segmenter.py`)
  - MujerTech segment (LATAM entrepreneurs)
  - Cascadia AI segment (PNW AI professionals)
  - Job Target segment (target company matching)
  - 50+ LATAM locations, 30+ PNW locations
  - AI/ML keyword detection

- **Resurrection Scanner** (`services/resurrection_scanner.py`)
  - Dormant relationship detection (301 found)
  - Broken promise detection (3 found)
  - Unanswered question detection (2 found)
  - "They're waiting" detection (16 found)
  - Pattern matching with context extraction

- **Message Generator** (`services/message_generator.py`)
  - Claude API integration (migrated to OpenAI in v0.4.0)
  - Segment-aware prompting
  - 7 message purposes (reconnect, introduce, etc.)
  - Multi-variation generation
  - Token usage tracking

- **API Routes**
  - `/api/upload/` - CSV file uploads
  - `/api/contacts/` - Contact CRUD with filtering
  - `/api/target-companies/` - Target company management
  - `/api/resurrection/` - Opportunity detection
  - `/api/generate/` - Message generation

#### Technical Details

- SQLAlchemy async with asyncpg driver
- Supabase PostgreSQL backend
- Pydantic schemas for validation
- Full API documentation at `/docs`

---

## [0.2.0] - 2026-01-27

### Phase 2: Playwright Module Complete

#### Added

- **LinkedIn Browser Service** (`linkedin_browser.py`)
  - Cookie-based authentication with manual login flow
  - Connection list scraping with pagination (max 50 items)
  - Follower list scraping with pagination (max 50 items)
  - Profile detail extraction (name, headline, location, experience, education)

- **Anti-Detection Measures**
  - User agent rotation (5 Chrome variants)
  - Viewport randomization
  - Random delays between actions (0.5-3s)
  - Human-like scrolling in steps
  - Locale and timezone settings

- **Error Handling**
  - Custom exceptions: `LinkedInError`, `AuthenticationError`, `ScrapingError`
  - Retry decorator with exponential backoff
  - Structured logging throughout

- **Debugging Tools**
  - `save_debug_snapshot()` method for HTML + screenshot capture
  - Debug files saved to `playwright-data/`

#### Technical Details

- Connections extracted from `<figure aria-label>` (stable selector)
- Followers extracted from profile links with text filtering
- Pagination stops after 3 scroll attempts with no new items
- Maximum 20 scroll attempts as safety limit

---

## [0.1.0] - 2026-01-08

### Phase 1: Initial Setup

#### Added

- **Backend (FastAPI)**
  - Basic application structure
  - Health check endpoint
  - CORS configuration for frontend
  - Pydantic settings for environment variables

- **Frontend (React + Vite)**
  - Initial React 19 setup
  - Tailwind CSS configuration
  - Health check component

- **Project Structure**
  - Monorepo layout (backend/frontend)
  - Python dependencies via `pyproject.toml`
  - Environment configuration template

#### Configuration

- Database URL (Supabase) configured but not connected
- Anthropic API key placeholder
- Rate limit settings defined

---

## Upcoming

### [0.6.0] - Planned: Contact Ranking

- Combined ranking algorithm (warmth + segment + opportunity)
- Priority queue for outreach
- Daily outreach recommendations

### [0.7.0] - Planned: Advanced Features

- LinkedIn profile enrichment (via scraper)
- Campaign management
- Analytics and reporting
- Scheduling suggestions

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | Jan 8, 2026 | Initial setup |
| 0.2.0 | Jan 27, 2026 | Playwright scraper |
| 0.3.0 | Feb 5, 2026 | Intelligence engine |
| 0.4.0 | Feb 6, 2026 | OpenAI + Queue workflow |
| 0.5.0 | Feb 6, 2026 | Frontend dashboard (dark theme) |
| 0.6.0 | TBD | Contact ranking |
| 0.7.0 | TBD | Advanced features |
