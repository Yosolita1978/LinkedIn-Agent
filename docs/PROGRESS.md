# LinkedIn Intelligence & Outreach Agent - Progress Report

**Date**: February 12, 2026
**Status**: Backend + Frontend + Contact Ranking + Follower Automation + Showcase Video Complete

---

## Project Vision

A personal intelligence tool for strategic LinkedIn outreach, supporting three use cases:

1. **MujerTech** - Women entrepreneurs in Latin America
2. **Cascadia AI** - AI/ML professionals in Pacific Northwest
3. **Job Search** - Networking with people at target companies

---

## What Was Built Today

### 1. Database Schema (6 Tables)

All tables created in Supabase via SQLAlchemy async:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `contacts` | LinkedIn connections | name, company, warmth_score, segment_tags, message stats |
| `messages` | Message history | direction, content, is_substantive |
| `resurrection_opportunities` | Outreach hooks | hook_type, hook_detail, is_active |
| `target_companies` | Job search targets | name, notes |
| `outreach_queue_items` | Message queue | status, generated_message |
| `data_uploads` | Upload tracking | file_type, records_processed |

**Files:**
- `backend/app/models/contact.py`
- `backend/app/models/message.py`
- `backend/app/models/resurrection.py`
- `backend/app/models/target_company.py`
- `backend/app/models/queue.py`
- `backend/app/models/upload.py`

---

### 2. LinkedIn Export Parser

Parses CSV files from LinkedIn data export:

- **Connections.csv** → Creates/updates contacts with name, company, email, connection date
- **messages.csv** → Creates messages linked to contacts, determines direction (sent/received)

**Features:**
- Skips sponsored/automated messages
- Handles group conversations gracefully
- Updates contact message statistics

**Results from your data:**
- 2,333 connections imported
- 5,823 messages imported
- 384 new contacts created from messages
- 1,441 contacts updated with message stats

**File:** `backend/app/services/export_parser.py`

---

### 3. Warmth Scoring Engine

Calculates relationship "warmth" (0-100) based on 5 factors:

| Factor | Max Points | Logic |
|--------|------------|-------|
| Recency | 30 | How recently you messaged (30 if <7 days, 0 if >180 days) |
| Frequency | 20 | Total message count (20 if 20+ messages) |
| Depth | 25 | Average message length + substantive ratio |
| Responsiveness | 15 | Balance of sent vs received (15 if balanced) |
| Initiation | 10 | Whether they initiate conversations |

**Substantive messages** = 100+ characters, not just "thanks", "congrats", etc.

**File:** `backend/app/services/warmth_scorer.py`

---

### 4. Audience Segmentation

Auto-tags contacts into segments based on keywords:

#### MujerTech Segment
- **Matches if:** Location is in LATAM (50+ locations/cities)
- **Keywords:** entrepreneur, founder, emprendedora, CEO, etc.

#### Cascadia AI Segment
- **Matches if:** Location is PNW (Seattle, Portland, Vancouver, etc.) AND has AI keywords
- **Keywords:** machine learning, AI, LLM, data science, etc.

#### Job Target Segment
- **Matches if:** Company matches a target company name

**File:** `backend/app/services/segmenter.py`

---

### 5. Resurrection Scanner

Detects outreach opportunities by analyzing patterns:

| Hook Type | What It Finds |
|-----------|---------------|
| `dormant` | Warm contacts (40+ warmth) with no messages in 60+ days |
| `promise_made` | Messages where you said "I'll...", "let me..." but didn't follow up |
| `question_unanswered` | They asked a question you never answered |
| `they_waiting` | Their last message was to you (ball in your court) |

**Your scan results:**
- 301 dormant relationships
- 3 broken promises
- 2 unanswered questions
- 16 people waiting on you

**File:** `backend/app/services/resurrection_scanner.py`

---

### 6. Message Generator (Claude API)

Generates personalized outreach messages using Claude:

**Inputs:**
- Contact profile (name, company, headline, about)
- Message history summary
- Segment context (MujerTech/Cascadia/Job Search)
- Resurrection hooks (if any)
- Purpose (reconnect, introduce, follow_up, etc.)

**Outputs:**
- 1-3 message variations
- Tailored to segment tone
- Uses resurrection hooks as openers

**Purposes available:**
- `reconnect` - Re-engage dormant relationship
- `introduce` - First meaningful connection
- `follow_up` - Continue previous conversation
- `invite_community` - Invite to event/community
- `ask_advice` - Request perspective
- `congratulate` - Celebrate achievement
- `share_resource` - Share something valuable

**File:** `backend/app/services/message_generator.py`

---

### 7. API Endpoints

All endpoints are live at `http://localhost:8000`:

#### Upload Routes (`/api/upload/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/connections` | Upload Connections.csv |
| POST | `/messages` | Upload messages.csv |
| GET | `/status` | Get upload stats |

#### Contacts Routes (`/api/contacts/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List with pagination, filtering, sorting |
| GET | `/top-warmth` | Get highest warmth contacts |
| GET | `/stats` | Overall statistics |
| GET | `/{id}` | Contact detail with warmth breakdown |
| PATCH | `/{id}/tags` | Update manual tags |
| POST | `/recalculate-warmth` | Recalculate all warmth scores |
| POST | `/segment` | Run audience segmentation |

#### Target Companies Routes (`/api/target-companies/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List all target companies |
| POST | `/` | Add single company |
| POST | `/bulk` | Add multiple companies |
| DELETE | `/{id}` | Remove company |

#### Resurrection Routes (`/api/resurrection/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/scan` | Run all scanners |
| POST | `/scan/{type}` | Run specific scanner |
| GET | `/opportunities` | List active opportunities |
| POST | `/opportunities/{id}/dismiss` | Mark as addressed |

#### Generate Routes (`/api/generate/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/message` | Generate message for contact |
| POST | `/batch` | Generate for multiple contacts |
| GET | `/purposes` | List available purposes |

#### Ranking Routes (`/api/ranking/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/recommendations` | Ranked outreach list (filter by segment, limit) |
| GET | `/recommendations/{id}` | Priority breakdown for one contact |

---

## Current Data Stats

From your LinkedIn export:

- **Total contacts:** 2,717 (2,333 from Connections.csv + 384 from messages)
- **Contacts with messages:** 1,441
- **Total messages:** 5,823
- **Resurrection opportunities:** 322

---

## What's Remaining

### Phase 1: Queue Management (Backend) — DONE
- [x] Queue routes for tracking message status (7 endpoints at `/api/queue/`)
- [x] Save generated messages to queue (as drafts)
- [x] Status workflow: draft → approved → sent → responded
- [x] Prevent duplicate outreach (one active item per contact)
- [x] Testing with frontend — validated via React dashboard

### Phase 2: OpenAI Migration — DONE
- [x] Switched from Anthropic Claude to OpenAI Agents SDK
- [x] Built-in Traces for observability (platform.openai.com/traces)
- [x] Removed langchain/langgraph dependencies

### Phase 3: Frontend Dashboard — DONE
- [x] React 19 + TypeScript + Vite 7 + Tailwind CSS 4
- [x] Dark theme UI (slate-800/900 backgrounds)
- [x] 5 pages: Dashboard, Contacts, Contact Detail, Queue, Opportunities
- [x] react-router-dom with sidebar navigation
- [x] Typed API layer (fetch wrappers for all backend endpoints)
- [x] Shared components: WarmthBadge, SegmentBadge, StatusBadge, LoadingSpinner, ErrorMessage, EmptyState

### Phase 4: Contact Ranking — DONE
- [x] Combined ranking algorithm: priority = warmth(40%) + segment(25%) + urgency(35%)
- [x] Backend service + 2 API endpoints (`/api/ranking/recommendations`, `/api/ranking/recommendations/{id}`)
- [x] "Today's Outreach" page with segment filter, priority badges, reasons, generate & queue flow
- [x] Dashboard preview card showing top 5 recommendations
- [x] Auto-dismiss resurrection opportunities when contact is added to queue

### Phase 5: Follower Connection Automation — DONE
- [x] LinkedIn Voyager API for fast profile enrichment (~1s vs ~10s with Playwright)
- [x] 3-phase connection flow: scan → generate notes → review/edit → send
- [x] All followers become candidates (not just segment-matched ones)
- [x] "general" segment for people with no specific match
- [x] Follower deduplication + self-filtering (own profile removed)
- [x] Graceful handling of "Add a note" button not found
- [x] Frontend: full FollowersPage with 7 phases, animated progress, note editing
- [x] Connection notes generated via OpenAI Agents SDK (GPT-4o)

### Phase 5b: Dashboard & Queue UX — DONE
- [x] Dashboard stat cards: "?" tooltips explaining each stat
- [x] Dashboard stat cards: clickable, navigate to relevant pages
- [x] Queue: AI message regeneration with custom instructions ("make it about Cascadia")
- [x] Queue: text input + Regenerate button in edit mode

### Phase 5c: Showcase Video + Developer Experience — DONE
- [x] Remotion v4 project in `video/` (36-second animated showcase, 1920x1080, 30fps)
- [x] 6 scenes: Intro, Dashboard, Contact Detail, Opportunities, AI Generation, Outro
- [x] Recreated UI as React components (laptop mockup, sidebar, warmth badges, animated bars)
- [x] Simulated interactions: cursor clicks, typing animation, tab switching, success banners
- [x] `TransitionSeries` with fade + slide transitions between scenes
- [x] Shared components: LaptopMockup, FadeIn, TypingAnimation, CursorClick, theme
- [x] Claude Code skill: `/render-video` — renders video from CLI with optional codec/scale args
- [x] `QUICKSTART.md` — local setup guide (backend + frontend)

### Phase 6: End-to-End Testing & Polish — NEXT
- [ ] Full end-to-end test of follower connection pipeline with real LinkedIn cookies
- [ ] Voyager API: validate encoded member ID endpoints with real data
- [ ] Error recovery: handle mid-scan browser crashes
- [ ] Performance: test Voyager vs Playwright enrichment times at scale

### Phase 7: Advanced Features
- [ ] LinkedIn profile enrichment for existing contacts (via Voyager API)
- [ ] Campaign management (group outreach sequences)
- [ ] Analytics and reporting dashboard
- [ ] Automated scheduling suggestions
- [ ] Export outreach history

---

## How to Run

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Environment Variables Needed

```bash
# backend/.env
DATABASE_URL=postgresql://...your-supabase-url...
OPENAI_API_KEY=sk-...your-openai-key...
APP_ENV=development
```

---

## Quick Test Commands

```bash
# Health check
curl http://localhost:8000/health

# Contact stats
curl http://localhost:8000/api/contacts/stats

# Top warmth contacts
curl "http://localhost:8000/api/contacts/top-warmth?limit=10"

# Resurrection opportunities
curl http://localhost:8000/api/resurrection/opportunities

# Generate message (replace <contact-id>)
curl -X POST http://localhost:8000/api/generate/message \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "<id>", "purpose": "reconnect"}'
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    LinkedIn Intelligence Agent               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LinkedIn Export (CSV)                                       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐ │
│  │ Export Parser│────▶│   Supabase   │◀────│  Segmenter  │ │
│  └──────────────┘     │   (6 tables) │     └─────────────┘ │
│                       └──────────────┘                      │
│                              │                               │
│         ┌────────────────────┼────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   Warmth    │     │Resurrection │     │  OpenAI     │   │
│  │   Scorer    │     │   Scanner   │     │  Generator  │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                    │                    │         │
│         └────────────────────┼────────────────────┘         │
│                              ▼                               │
│                       ┌─────────────┐                       │
│                       │ FastAPI API │                       │
│                       │ (9 routers) │                       │
│                       └─────────────┘                       │
│                              │                               │
│                       ┌─────────────┐                       │
│                       │  Voyager    │  ← LinkedIn internal  │
│                       │  API Client │    REST API (fast)    │
│                       └─────────────┘                       │
│                              │                               │
│                       ┌─────────────┐                       │
│                       │  Playwright │  ← Browser fallback   │
│                       │  Browser    │    + Connection send   │
│                       └─────────────┘                       │
│                              │                               │
│                              ▼                               │
│                       ┌─────────────┐                       │
│                       │  Frontend   │  ← React 19 + Dark   │
│                       │   (React)   │    Theme Dashboard    │
│                       └─────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

#### Follower Routes (`/api/followers/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/scan` | Scan followers: scrape, deduplicate, enrich via Voyager/Playwright, segment |
| POST | `/generate-notes` | Generate personalized connection notes (AI) for review |
| POST | `/connect` | Send connection requests with user-approved notes |

#### Queue Routes (`/api/queue/`) — Updated
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/{id}/regenerate` | Regenerate message with custom AI instruction |

---

## Next Session Priorities

1. **End-to-End Testing** - Test the full follower connection pipeline with real LinkedIn cookies and a running backend
2. **Voyager API Validation** - Confirm encoded member ID endpoints work with real LinkedIn data
3. **Profile Enrichment** - Use Voyager API to fill in missing data for existing contacts
4. **Advanced Features** - Campaign management, analytics, automated scheduling
