# Phase 6: End-to-End Testing Report

**Date:** 2026-02-10
**Environment:** macOS, Backend on localhost:8000, Frontend on localhost:5173

---

## Prerequisites

Before running E2E tests, ensure:

1. **Backend `.env`** has valid `DATABASE_URL` and `OPENAI_API_KEY`
2. **LinkedIn session** is authenticated:
   ```bash
   cd backend && source .venv/bin/activate
   uv run python test_auth.py
   ```
   - Log in manually in the browser window
   - Wait for "Login successful! Cookies saved." AND "Saved storage state to..."
   - This saves both `playwright-data/cookies.json` and `playwright-data/storage_state.json`
3. **Backend running:**
   ```bash
   cd backend && source .venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```
4. **Frontend running:**
   ```bash
   cd frontend && npm run dev
   ```

---

## Test Results Summary

| # | Test Area | Endpoint(s) | Result | Notes |
|---|-----------|-------------|--------|-------|
| 1 | Backend health | `GET /`, `GET /health` | PASS | API running, env=development |
| 2 | Frontend health | All 7 routes | PASS | Vite serving, all pages return 200 |
| 3 | CORS preflight | `OPTIONS /api/contacts/stats` | PASS | `Access-Control-Allow-Origin: http://localhost:5173` |
| 4 | Contacts — stats | `GET /api/contacts/stats` | PASS | 2,717 contacts, warmth distribution returned |
| 5 | Contacts — list | `GET /api/contacts?limit=3` | PASS | Paginated list with all fields |
| 6 | Contacts — detail | `GET /api/contacts/{id}` | PASS | Full profile + message metadata + resurrection opportunities |
| 7 | Contacts — top warmth | `GET /api/contacts/top-warmth?limit=5` | PASS | Sorted by warmth_score, includes warmth_breakdown |
| 8 | Ranking recommendations | `GET /api/ranking/recommendations?limit=3` | PASS | Priority scores + resurrection hooks |
| 9 | Resurrection opportunities | `GET /api/resurrection/opportunities?limit=3` | PASS | 317 opportunities (they_waiting, promise_made) |
| 10 | Message purposes | `GET /api/generate/purposes` | PASS | 7 purposes returned |
| 11 | Message generation | `POST /api/generate/message` | PASS | OpenAI generated 2 variations (631 tokens) |
| 12 | Queue — add item | `POST /api/queue/` | PASS | Created draft with contact join |
| 13 | Queue — list | `GET /api/queue/` | PASS | Returns items with contact_name, contact_company |
| 14 | Queue — get item | `GET /api/queue/{id}` | PASS | Full item detail |
| 15 | Queue — edit message | `PATCH /api/queue/{id}/message` | PASS | Updated message text, status stays draft |
| 16 | Queue — regenerate | `POST /api/queue/{id}/regenerate` | PASS | OpenAI generated new variation with custom_instruction |
| 17 | Queue — status: draft→approved | `PATCH /api/queue/{id}/status` | PASS | approved_at timestamp set |
| 18 | Queue — status: approved→sent | `PATCH /api/queue/{id}/status` | PASS | sent_at timestamp set |
| 19 | Queue — status: sent→responded | `PATCH /api/queue/{id}/status` | PASS | replied_at timestamp set |
| 20 | Queue — delete | `DELETE /api/queue/{id}` | PASS | Returns 404 on subsequent GET |
| 21 | Queue — stats | `GET /api/queue/stats` | PASS | Counts by status and use_case |
| 22 | Followers — scan | `POST /api/followers/scan` | PASS | 5 scraped, 3 enriched via Voyager API |
| 23 | Voyager API auth | `GET /voyager/api/me` | PASS | Authenticated with fresh cookies |
| 24 | Voyager — public profile | `get_profile("poraschi")` | PASS | Name, headline returned |
| 25 | Voyager — private profile | `get_profile("ACoAACbm...")` | PASS | Returns real name (not error text) |

---

## Detailed Test Procedures

### 1. Backend & Frontend Health

```bash
# Backend
curl -s http://localhost:8000/ | python3 -m json.tool
curl -s http://localhost:8000/health | python3 -m json.tool

# Frontend — all routes return 200
for route in / /contacts /queue /opportunities /recommendations /target-companies /followers; do
  curl -s http://localhost:5173$route -o /dev/null -w "%{http_code} $route\n"
done

# CORS preflight
curl -s -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/contacts/stats -D - -o /dev/null
```

**Expected:** Backend returns `{"status": "healthy"}`. All frontend routes return 200. CORS header includes `access-control-allow-origin: http://localhost:5173`.

### 2. Contacts Endpoints

```bash
# Stats
curl -s http://localhost:8000/api/contacts/stats | python3 -m json.tool

# List (paginated)
curl -s "http://localhost:8000/api/contacts?limit=3" | python3 -m json.tool

# Top warmth
curl -s "http://localhost:8000/api/contacts/top-warmth?limit=5" | python3 -m json.tool

# Detail (use a real contact ID from the list)
curl -s "http://localhost:8000/api/contacts/{contact_id}" | python3 -m json.tool
```

**Expected:** Stats show total_contacts > 0 and warmth_distribution. List returns contacts with name, company, warmth_score. Top-warmth sorted descending with warmth_breakdown. Detail includes message_metadata and resurrection_opportunities.

### 3. Ranking & Resurrection

```bash
curl -s "http://localhost:8000/api/ranking/recommendations?limit=3" | python3 -m json.tool
curl -s "http://localhost:8000/api/resurrection/opportunities?limit=3" | python3 -m json.tool
```

**Expected:** Recommendations include priority_score, priority_breakdown, reasons, and resurrection_hooks. Opportunities include hook_type (they_waiting, promise_made, etc.) and hook_detail.

### 4. Message Generation (requires OpenAI API key)

```bash
# List purposes
curl -s http://localhost:8000/api/generate/purposes | python3 -m json.tool

# Generate message (use a real contact_id)
curl -s -X POST http://localhost:8000/api/generate/message \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "{contact_id}", "purpose": "reconnect", "num_variations": 2}' \
  | python3 -m json.tool
```

**Expected:** Returns contact info, purpose, and 2 message variations. tokens_used > 0.

### 5. Queue Lifecycle

```python
# Best tested via Python to avoid shell escaping issues:
import json, urllib.request

BASE = "http://localhost:8000/api/queue"

def api(method, path, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body,
        headers={"Content-Type": "application/json"}, method=method)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Create draft
item = api("POST", "/", {
    "contact_id": "{contact_id}",
    "use_case": "cascadia",
    "outreach_type": "warm",
    "purpose": "reconnect",
    "generated_message": "Test message"
})
item_id = item["id"]

# Edit message
api("PATCH", f"/{item_id}/message", {"generated_message": "Updated message"})

# Regenerate (calls OpenAI)
api("POST", f"/{item_id}/regenerate", {"custom_instruction": "Make it about AI"})

# Status transitions
api("PATCH", f"/{item_id}/status", {"status": "approved"})   # draft → approved
api("PATCH", f"/{item_id}/status", {"status": "sent"})       # approved → sent
api("PATCH", f"/{item_id}/status", {"status": "responded"})  # sent → responded

# Delete (create a new draft first — sent/responded items can't be deleted)
draft = api("POST", "/", {
    "contact_id": "{contact_id}",
    "use_case": "cascadia",
    "outreach_type": "warm",
    "purpose": "reconnect",
    "generated_message": "To be deleted"
})
api("DELETE", f"/{draft['id']}", None)
```

**Expected:** Each status transition sets the corresponding timestamp (approved_at, sent_at, replied_at). Delete returns `{"detail": "Queue item deleted"}`. GET after delete returns 404.

### 6. Followers Scan (requires LinkedIn session)

```bash
curl -s -X POST http://localhost:8000/api/followers/scan \
  -H "Content-Type: application/json" \
  -d '{"max_followers": 5, "max_profiles": 3}' \
  | python3 -m json.tool
```

**Expected:** Returns candidates array with name, headline, profile_url, segments. Stats show followers_scraped, profiles_enriched. A Chromium window will open briefly (headless=False required by LinkedIn).

**Note:** Use small limits (max_followers=5, max_profiles=3) to avoid LinkedIn rate limiting.

---

## Bugs Found & Fixed

### Bug 1: Private profile error text leaking as candidate name

**Symptom:** When Voyager API encounters a private/restricted profile with expired cookies, LinkedIn returns an error message like `The profile "acoaac..." may be private.` which gets parsed as the person's name.

**Root cause:** Voyager parsers (`_parse_profile_view`, `_parse_dash_profile`, `_parse_mini_profile`) only checked `if profile["name"]` (truthy), not whether the name was a real person name.

**Fix:** Added `_is_valid_name()` method in `linkedin_voyager.py` that rejects names containing error phrases (`"may be private"`, `"profile"`, `"linkedin member"`, `"not found"`). All three parsers now use this validation. When rejected, the profile returns `None`, causing the follower connector to fall back to the original follower name from the list scrape.

**File:** `backend/app/services/linkedin_voyager.py`

### Bug 2: LinkedIn blocking headless Chromium

**Symptom:** `POST /api/followers/scan` returns 401 "LinkedIn session not authenticated" even with valid cookies.

**Root cause:** LinkedIn detects and blocks headless Chromium browsers. The `is_logged_in()` check navigates to the feed page, but LinkedIn redirects to login when it detects automation.

**Fix (two parts):**

1. **Storage state persistence** (`linkedin_browser.py`): Changed from saving/loading just cookies to using Playwright's full `storageState` (cookies + localStorage + sessionStorage). After `test_auth.py` manual login, the full browser state is saved to `playwright-data/storage_state.json`. On startup, this state is loaded into the browser context.

2. **Non-headless scan** (`followers.py`): Changed `get_authenticated_browser()` to use `headless=False`. A visible browser window opens during scans. Also added `--disable-blink-features=AutomationControlled` launch arg.

**Files:** `backend/app/services/linkedin_browser.py`, `backend/app/routes/followers.py`

---

## Known Issues (non-blocking)

### Playwright profile scraper returns empty fields

**Symptom:** `scrape_profile()` returns empty name, headline, location, company for all profiles.

**Impact:** Low — the Voyager API handles profile enrichment successfully. Playwright scraping is only used as a fallback.

**Cause:** LinkedIn changed their DOM structure. The CSS selectors in `scrape_profile()` no longer match the current page HTML.

**Recommended fix:** Update the selectors in `linkedin_browser.py` `scrape_profile()` method, or remove the Playwright profile scraping fallback entirely since the Voyager API is faster and more reliable.

---

## Valid Enum Values (reference)

| Field | Valid Values |
|-------|-------------|
| `use_case` | `mujertech`, `cascadia`, `job_search` |
| `outreach_type` | `resurrection`, `warm`, `cold` |
| `purpose` | `reconnect`, `introduce`, `follow_up`, `invite_community`, `ask_advice`, `congratulate`, `share_resource` |
| `status` | `draft`, `approved`, `sent`, `responded` |
