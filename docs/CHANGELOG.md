# Changelog

All notable changes to this project are documented here.

---

## [0.9.0] - 2026-02-12

### Remotion Showcase Video + Claude Code Skill

#### Added — Remotion Video Project (`video/`)

- **Programmatic showcase video** built with Remotion v4 (React-based video framework)
  - 36-second highlight reel at 1920x1080, 30fps
  - 6 animated scenes with `TransitionSeries` (fade + slide transitions)
  - Recreated simplified versions of the real app UI — no screenshots, all React components
  - Dark theme matching the real frontend (slate-900 bg, same warmth colors)

- **6 Scenes:**
  1. **Intro** (4s) — Logo + tagline with glow effect, spring animation
  2. **Dashboard** (9s) — 6 stat cards stagger in, warmth distribution bar grows, segment bar, top contacts list
  3. **Contact Detail** (9s) — "Maria Rodriguez" HOT 92, 5 warmth breakdown bars animate from 0% to target width (hero animation)
  4. **Opportunities** (6s) — 3 resurrection hook cards, cursor switches "Dormant" tab, clicks "Generate & Queue"
  5. **AI Generation** (7s) — Click Generate → spinner → typing animation writes personalized message → select variation → Add to Queue → success banner
  6. **Outro** (3.5s) — Logo + tech stack attribution

- **Shared Components:**
  - `LaptopMockup.tsx` — CSS browser chrome (traffic lights, URL bar) + sidebar with real nav icons
  - `FadeIn.tsx` — Reusable staggered opacity + translateY animation
  - `TypingAnimation.tsx` — Character-by-character typewriter with blinking cursor
  - `CursorClick.tsx` — Animated cursor movement with click ripple effect (spring physics)
  - `theme.ts` — All colors matching the real app

- **Project structure:** `video/` folder alongside `backend/` and `frontend/`
  - Remotion v4, React 19, TypeScript
  - `npm run studio` for browser preview, `npm run render` for MP4 output

#### Added — Claude Code Skill (`/render-video`)

- **`.claude/skills/render-video/SKILL.md`** — Custom slash command for rendering
  - `/render-video` — Render with defaults (H.264, 1080p)
  - `/render-video --codec gif --scale 0.5` — Custom codec/scale
  - Installs deps automatically if needed
  - Reports output file path and size

#### Added — Quick Start Guide

- **`QUICKSTART.md`** at project root — Short guide on how to start the project locally (backend + frontend)

---

## [0.8.0] - 2026-02-09

### Phase 5 Complete: Follower Connection Automation + UX Improvements

#### Added — Follower Connection Pipeline

- **LinkedIn Voyager API** (`services/linkedin_voyager.py`) — NEW
  - Fast profile enrichment via LinkedIn's internal REST API (~1s per profile vs ~10s with Playwright)
  - Cookie-based auth using existing `li_at` and `JSESSIONID` cookies
  - Handles both vanity URLs (`/in/john-doe`) and encoded member IDs (`ACoAAA...`)
  - Tries 3 endpoint strategies: `profileView`, `dash/profiles`, `miniProfiles`
  - Falls back to Playwright browser scraping if Voyager fails

- **3-Phase Connection Flow** (scan → generate notes → review/edit → send)
  - `POST /api/followers/scan` — Scrape followers, deduplicate, enrich via Voyager/Playwright, segment
  - `POST /api/followers/generate-notes` — AI-generated personalized connection notes (≤300 chars)
  - `POST /api/followers/connect` — Send connection requests with user-reviewed notes
  - All followers become candidates (not just segment-matched ones)
  - "general" segment context added for people with no specific segment match

- **Follower Deduplication & Self-Filtering**
  - URL normalization for consistent comparison
  - Removes duplicate entries from scroll pagination
  - Filters out user's own profile (URL-based + frequency-based detection)

- **Connection Request Handling**
  - `send_connection_request()` in LinkedInBrowser — navigates to profile, clicks Connect, adds note
  - When "Add a note" button isn't found, returns `note_not_supported` status with the note for manual copy
  - Rate limiting: 15-30 seconds between connection requests

#### Added — Dashboard Improvements

- **Tooltip "?" icons** on all 5 stat cards (hover to see what each stat means)
- **Clickable stat cards** — Total Contacts → `/contacts`, Queue Drafts → `/queue`, Opportunities → `/opportunities`

#### Added — Queue AI Regeneration

- `POST /api/queue/{item_id}/regenerate` — Regenerate a draft message with custom AI instructions
  - Accepts `custom_instruction` (e.g. "make it about Cascadia", "shorter", "more casual")
  - Uses the queue item's existing contact/purpose/segment context
  - Returns new message without auto-saving — user decides
- **Frontend**: text input + purple "Regenerate" button in the queue edit view
  - Press Enter or click to regenerate; spinner during generation
  - New message replaces textarea content; user can still edit before saving

#### Added — Frontend Components

- **FollowersPage** (`/followers`) — Full workflow UI with 7 phases:
  - idle → scanning → candidates → generating → reviewing → connecting → results
  - `ScanProgress` component: animated step-by-step checklist with profile counter and elapsed timer
  - Candidate selection with checkboxes, segment badges, LinkedIn profile links
  - Note review phase: editable textareas (300 char limit), remove candidates, back navigation
  - Results: per-candidate status badges (Sent, Already Connected, Manual Note Needed, Failed)
  - Copy-to-clipboard for manual notes
- **SegmentBadge** component for mujertech/cascadia/job_target badges

#### Changed

- `follower_connector.py` — Major rewrite:
  - Voyager API first, Playwright fallback for enrichment
  - Reduced delays (0.5-1.5s for Voyager, 1.0-2.5s for browser)
  - All enriched profiles become candidates (not just segment-matched)
  - Separate `generate_notes_for_candidates()` function
  - `connect_with_candidates()` now expects pre-reviewed notes
- `linkedin_browser.py` — Performance + reliability:
  - Reduced navigation delays and scroll rounds
  - Multiple CSS selector fallbacks for profile fields
  - `get_own_profile_url()` method
  - `send_connection_request()` graceful handling of missing "Add a note" button

#### Fixed

- Empty profile data from LinkedIn scraping (CSS selectors updated with multiple fallbacks)
- Voyager API HTTP 410 for encoded member IDs (added multiple endpoint strategies)
- Own profile appearing 7x in candidates (URL + frequency filtering)
- Duplicate followers from scroll pagination (URL deduplication)
- Connection notes crash on empty segment list (`segments[0]` → `segments[0] if segments else "general"`)

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

### [0.9.0] - Planned: End-to-End Testing & Polish

- Full end-to-end testing of follower connection pipeline (needs LinkedIn cookies + running backend)
- Voyager API encoded member ID endpoints may need further testing with real data
- Error recovery: handle mid-scan browser crashes gracefully
- Campaign management (group outreach sequences)

### [1.0.0] - Planned: Advanced Features

- LinkedIn profile enrichment for existing contacts (via Voyager API)
- Analytics and reporting dashboard
- Automated scheduling suggestions
- Export outreach history

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | Jan 8, 2026 | Initial setup |
| 0.2.0 | Jan 27, 2026 | Playwright scraper |
| 0.3.0 | Feb 5, 2026 | Intelligence engine |
| 0.4.0 | Feb 6, 2026 | OpenAI + Queue workflow |
| 0.5.0 | Feb 6, 2026 | Frontend dashboard (dark theme) |
| 0.8.0 | Feb 9, 2026 | Follower automation + Voyager API + Dashboard/Queue UX |
| 0.9.0 | Feb 12, 2026 | Remotion showcase video + /render-video Claude skill + QUICKSTART.md |
