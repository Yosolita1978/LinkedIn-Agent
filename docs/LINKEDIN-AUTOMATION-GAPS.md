# LinkedIn Automation Gaps & Build Plan

> **Purpose:** Reference document mapping all missing features to fully automate personal LinkedIn usage.
> **Benchmarked against:** BearConnect.io (commercial tool, $67-285/mo)
> **Created:** March 18, 2026
> **Scope:** Personal use only — no multi-account, auth, or agency features.

---

## What You Already Have

| Feature | Details |
|---------|---------|
| AI message generation | Segment-aware, warmth-aware, purpose-driven (gpt-4o) |
| Warmth scoring | 5-component (recency, frequency, depth, responsiveness, initiation) |
| Network archetype | 5 types with tailored strategies |
| Resurrection detection | Dormant, broken promises, unanswered questions, they're waiting |
| Daily recommendations | AI-ranked priority contacts with reasons |
| Follower automation | Scan → enrich → generate notes → connect |
| CSV import | Connections + messages from LinkedIn export |
| Dashboard | Stats, warmth distribution, segments, top companies, archetype |
| Queue system | Draft → approved → sent → responded |
| Playwright automation | Profile scraping, follower scanning, connection sending |
| Voyager API | Fast profile enrichment (~1s per profile) |

---

## 8 Gaps to Fill

### Gap 1: Campaign Sequences

**Current state:** One message per contact. No follow-ups.

**What's missing:** After sending a connection request, there's no automated way to send a welcome message on Day 3 and share a resource on Day 7.

**Build steps:**

1. Create a `sequences` table in Supabase:
   - `id`, `name`, `steps` (JSON array of `{step_number, delay_days, message_purpose, template_context}`)
   - `created_at`, `updated_at`

2. Create a `sequence_enrollments` table:
   - `id`, `contact_id`, `sequence_id`, `current_step`, `status` (active/paused/completed/replied)
   - `next_action_at` (timestamp for when the next step should fire)
   - `started_at`, `completed_at`

3. Backend: `backend/app/models/sequence.py` — SQLAlchemy models
4. Backend: `backend/app/services/sequence_service.py` — Logic to:
   - Enroll a contact in a sequence
   - Check for due steps (where `next_action_at <= now` and `status = active`)
   - Generate the message for the current step using existing AI service
   - Add the message to the queue as a draft
   - Advance to next step (or complete) after message is sent
   - Auto-stop if contact replies (check responded status in queue)

5. Backend: `backend/app/routes/sequences.py` — CRUD endpoints
6. Frontend: `frontend/src/pages/Sequences.tsx` — List/create/edit sequences
7. Frontend: Add "Enroll in sequence" button on Contact Detail page

**Key design decision:** Sequence steps create queue items as drafts. You still review and approve them. The automation is in the *scheduling and generation*, not in unsupervised sending.

---

### Gap 2: Smart Scheduling

**Current state:** Everything is manual and immediate. Approved messages sit until you manually trigger them.

**What's missing:** A send window that automatically processes approved queue items at natural times.

**Build steps:**

1. Add columns to `queue_items` table:
   - `scheduled_for` (nullable timestamp — when to send)
   - `send_window_start` (e.g., "09:00")
   - `send_window_end` (e.g., "18:00")

2. Add to `backend/app/config.py`:
   ```python
   SEND_WINDOW_START: str = "09:00"  # PST
   SEND_WINDOW_END: str = "18:00"
   SEND_WINDOW_DAYS: list = ["mon", "tue", "wed", "thu", "fri"]
   SEND_WINDOW_TIMEZONE: str = "America/Los_Angeles"
   ```

3. Backend: `backend/app/services/scheduler_service.py`:
   - `get_next_send_time()` — find next valid time within send window
   - `process_scheduled_items()` — find approved items where `scheduled_for <= now`, send them via Playwright
   - Respect rate limit: count today's sent items, stop if >= `RATE_LIMIT_MESSAGES_PER_DAY`
   - Add random delays between sends (1-5 minutes apart, not seconds)

4. Backend: `backend/app/routes/scheduler.py`:
   - `POST /api/scheduler/start` — begin processing
   - `POST /api/scheduler/stop` — pause
   - `GET /api/scheduler/status` — current state, next scheduled send

5. Frontend: Add scheduling controls to Queue page:
   - "Schedule for" date/time picker on each queue item
   - "Auto-schedule all approved" button
   - Scheduler status indicator

**Key design decision:** This needs a background task runner. Options:
- **Simple:** A FastAPI background task that runs on an interval (e.g., every 5 minutes checks for due items)
- **Better:** APScheduler or Celery for reliable job scheduling
- **Simplest for personal use:** A cron job or `asyncio` loop in the FastAPI app

---

### Gap 3: LinkedIn Inbox Sync

**Current state:** Messages only appear after manually downloading CSV from LinkedIn and importing.

**What's missing:** Automatic fetching of conversations so you can see replies and new messages.

**Build steps:**

1. Research Voyager API messaging endpoints:
   - `GET /voyager/api/messaging/conversations` — list conversations
   - `GET /voyager/api/messaging/conversations/{id}/events` — messages in a conversation
   - These are unofficial endpoints; test with your cookies first

2. Backend: `backend/app/services/inbox_service.py`:
   - `fetch_conversations(limit=50)` — get recent conversations from Voyager
   - `sync_messages(conversation_id)` — pull messages and upsert into your `messages` table
   - `detect_new_replies()` — compare with last sync, flag new incoming messages
   - `get_inbox(page, filters)` — query your messages table, grouped by contact, sorted by recency

3. Backend: `backend/app/routes/inbox.py`:
   - `POST /api/inbox/sync` — trigger a sync
   - `GET /api/inbox` — list conversations (paginated, filterable)
   - `GET /api/inbox/{contact_id}` — full conversation with a contact

4. Add to `messages` table:
   - `synced_at` (timestamp of last sync)
   - `needs_reply` (boolean — their last message is unanswered)
   - `conversation_id` (LinkedIn conversation ID for linking)

5. Frontend: `frontend/src/pages/Inbox.tsx`:
   - Conversation list (left panel) + message thread (right panel)
   - "Sync now" button
   - Filter: all / needs reply / waiting for them
   - Badge count for "needs reply"

6. Add "Needs Reply" count to Dashboard overview

**Key risk:** Voyager messaging endpoints may require different auth or have stricter rate limits. Test manually first with curl before building.

---

### Gap 4: Content Scheduling

**Current state:** The tool only handles DMs and connection requests. No post creation.

**What's missing:** Composing, scheduling, and auto-publishing LinkedIn posts.

**Build steps:**

1. Create a `posts` table in Supabase:
   - `id`, `content` (text), `image_url` (nullable)
   - `status` (draft/scheduled/published/failed)
   - `scheduled_for` (timestamp)
   - `published_at` (timestamp)
   - `linkedin_post_id` (nullable, after publishing)
   - `engagement_stats` (JSON: likes, comments, reposts — nullable)
   - `created_at`, `updated_at`

2. Backend: `backend/app/models/post.py` — SQLAlchemy model
3. Backend: `backend/app/services/content_service.py`:
   - `create_post(content, image_url, scheduled_for)` — save draft/scheduled post
   - `publish_post(post_id)` — use Playwright to:
     - Navigate to linkedin.com/feed
     - Click "Start a post"
     - Type content
     - (Optional) Upload image
     - Click "Post"
     - Save the resulting post URL
   - `check_scheduled_posts()` — find posts where `scheduled_for <= now` and `status = scheduled`, publish them
   - `fetch_engagement(post_id)` — scrape likes/comments count from post URL

4. Backend: `backend/app/routes/content.py`:
   - `POST /api/posts` — create/schedule a post
   - `GET /api/posts` — list posts with filters
   - `PUT /api/posts/{id}` — edit draft
   - `DELETE /api/posts/{id}` — delete draft
   - `POST /api/posts/{id}/publish` — publish now
   - `POST /api/posts/check-scheduled` — trigger scheduled post check

5. Frontend: `frontend/src/pages/Content.tsx`:
   - Post composer (textarea + image upload)
   - Calendar view showing scheduled posts
   - List of past posts with engagement stats
   - "Schedule" vs "Post Now" buttons

**Key design decision:** Playwright post publishing is fragile (LinkedIn changes their DOM). Keep the selectors in a config/constant file for easy updates. Consider using multiple fallback selectors like you already do for connection requests.

---

### Gap 5: LinkedIn Search Import

**Current state:** You find new contacts only through follower scanning or CSV import.

**What's missing:** Importing contacts from LinkedIn search results (by role, company, location, etc.).

**Build steps:**

1. Backend: `backend/app/services/search_import_service.py`:
   - `scrape_search_results(search_url, max_results=50)`:
     - Open the LinkedIn search URL in Playwright
     - Scroll through results pages
     - Extract: name, headline, profile URL, location, current company
     - Return list of profile data
   - `import_search_results(profiles, auto_segment=True)`:
     - Deduplicate against existing contacts (by LinkedIn URL)
     - Create new contacts
     - Run segmentation on new contacts
     - Return import summary (new, skipped, enriched)

2. Backend: `backend/app/routes/search_import.py`:
   - `POST /api/search-import` — body: `{search_url, max_results}`
   - Returns: list of found profiles for user review
   - `POST /api/search-import/confirm` — body: `{profile_urls: [...]}`
   - Imports selected profiles as contacts

3. Frontend: `frontend/src/pages/SearchImport.tsx`:
   - Input field for LinkedIn search URL
   - "Scan" button → shows loading → displays results
   - Checkboxes to select which profiles to import
   - "Import Selected" button
   - Results summary (X new, Y already existed)

4. Add "Search Import" link to the navigation sidebar

**Key risk:** LinkedIn search pages have aggressive anti-scraping. Use slow scrolling, random delays, and limit to ~50 results per session. Don't run this too frequently.

---

### Gap 6: Contact Notes

**Current state:** Contacts only have tags for organization. No freeform notes.

**What's missing:** A place to write "met at PyCon", "wants to collaborate on AI project", etc.

**Build steps:**

1. Add `notes` column to `contacts` table:
   ```sql
   ALTER TABLE contacts ADD COLUMN notes TEXT;
   ```

2. Update `backend/app/models/contact.py` — add `notes = Column(Text, nullable=True)`
3. Update `backend/app/schemas/contact.py` — add `notes: Optional[str]` to schemas
4. Update `backend/app/routes/contacts.py` — allow updating notes via PUT
5. Update `backend/app/services/message_generator.py`:
   - Include contact notes in the AI context when generating messages
   - Add to the system prompt: "The user has noted the following about this person: {notes}"

6. Frontend: `frontend/src/pages/ContactDetail.tsx`:
   - Add an editable notes section (textarea with save button)
   - Show notes in the contact info panel

**This is the simplest gap to fill — start here.**

---

### Gap 7: Safety & Reliability Fixes

**Current state:** Rate limits configured but never enforced. Cookies can expire silently. Basic delays only.

**Build steps:**

**7a. Enforce rate limits (~1 hour):**
1. In `backend/app/services/queue_service.py`, before sending any message:
   ```python
   today_sent_count = await db.execute(
       select(func.count(QueueItem.id))
       .where(QueueItem.status == "sent")
       .where(func.date(QueueItem.sent_at) == date.today())
   )
   if today_sent_count >= settings.RATE_LIMIT_MESSAGES_PER_DAY:
       raise RateLimitExceeded("Daily message limit reached")
   ```
2. Return the limit status in queue stats endpoint
3. Show remaining daily quota on the Queue page

**7b. Cookie expiry detection (~2 hours):**
1. In `backend/app/services/voyager_service.py`, wrap API calls:
   - If response status is 401 or 403 → set a "cookies_expired" flag
   - Add endpoint: `GET /api/auth/status` — returns cookie validity
2. Frontend: Show a warning banner when cookies are expired
3. Include instructions on how to refresh cookies

**7c. Smarter delays (~2 hours):**
1. In `backend/app/services/playwright_service.py`:
   - Replace fixed 0.5-2s delays with variable delays:
     - Between messages: 1-5 minutes (not seconds)
     - Add occasional long pauses (10-30 seconds) to mimic reading
     - Vary by time of day (slower in early morning/late night)
   - Add a `delay_profile` config: "cautious" (longer) vs "normal"

**7d. Warm-up mode (~2 hours):**
1. Track daily activity count in a simple table or config
2. For first 7 days of use (or after 14+ days inactive):
   - Day 1-2: max 5 actions/day
   - Day 3-4: max 15 actions/day
   - Day 5-7: max 30 actions/day
   - Day 8+: normal limit (50/day)

---

### Gap 8: Configurable Persona

**Current state:** "Cristina Rodriguez, tech professional in Seattle" is hardcoded in `message_generator.py`.

**Build steps:**

1. Add persona config to `backend/app/config.py`:
   ```python
   PERSONA_NAME: str = "Cristina Rodriguez"
   PERSONA_TITLE: str = "Tech Professional"
   PERSONA_LOCATION: str = "Seattle"
   PERSONA_BIO: str = "..."
   PERSONA_INTERESTS: str = "AI, community building, Latin American tech"
   PERSONA_TONE: str = "warm, authentic, professional but friendly"
   ```

2. Update `backend/app/services/message_generator.py`:
   - Replace all hardcoded persona references with `settings.PERSONA_*`
   - Build system prompt dynamically from persona fields

3. Add endpoint: `GET /api/settings/persona` and `PUT /api/settings/persona`
4. Frontend: `frontend/src/pages/Settings.tsx` (or add to Dashboard):
   - Form with persona fields
   - "Save" button that updates .env or a settings table

**Alternative (simpler):** Just use .env variables and skip the UI. Edit .env when persona changes.

---

## Build Order Checklist

Copy this checklist and check off items as you build them:

### Phase 1 — Quick Fixes (a few hours) — DONE (March 23, 2026)
- [x] Gap 6: Add `notes` column + UI (simplest change)
- [x] Gap 7a: Enforce rate limits in queue service
- [x] Gap 8: Move persona to config/env vars
- [x] Gap 7b: Cookie expiry detection + warning banner

### Phase 2 — Core Automation (1-2 weeks) — IN PROGRESS
- [ ] Gap 2: Smart scheduling (send window + auto-send) — **SKIPPED** (not needed for now)
- [x] Gap 3: LinkedIn inbox sync — Playwright-based (Voyager messaging API returns 500, deprecated by LinkedIn)
- [ ] Gap 1: Multi-step sequences (follow-up automation)

### Phase 3 — Growth Features (2-3 weeks)
- [ ] Gap 4: Content composer + scheduling + auto-publish
- [ ] Gap 5: LinkedIn search URL import
- [ ] Gap 7c: Smarter delays
- [ ] Gap 7d: Warm-up mode
- [ ] Gap 9: Follower engagement strategy (see below)

### Phase 4 — Polish
- [ ] Campaign analytics (acceptance rate, reply rate per sequence)
- [ ] CSV export for contacts and analytics
- [ ] Dashboard integration for inbox badge, scheduled posts, active sequences
