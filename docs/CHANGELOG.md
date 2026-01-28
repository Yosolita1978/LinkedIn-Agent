# Changelog

All notable changes to this project are documented here.

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

### [0.3.0] - Planned

- Database integration (store scraped contacts)
- API endpoints for CRUD operations
- Background job queue for scraping

### [0.4.0] - Planned

- Frontend dashboard
- Contact list display
- Profile viewer

### [0.5.0] - Planned

- Claude AI integration
- Message generation
- Campaign management

---

## Version History Summary

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | Jan 8, 2026 | Initial setup |
| 0.2.0 | Jan 27, 2026 | Playwright module complete |
| 0.3.0 | TBD | Database integration |
| 0.4.0 | TBD | Frontend dashboard |
| 0.5.0 | TBD | AI integration |
