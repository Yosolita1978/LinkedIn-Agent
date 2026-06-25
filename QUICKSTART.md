# Quick Start Guide

Get the LinkedIn Outreach Agent running locally: backend API, frontend dashboard,
database, and a LinkedIn session — then use the follower → conversation workflow.

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** (for `npm`)
- **`uv`** (Python package manager) — https://docs.astral.sh/uv/
- A **Supabase Postgres** database (connection string)
- An **OpenAI API key** (used for AI message generation, gpt-4o)

---

## 1. Backend (FastAPI — port **8000**)

> The frontend hardcodes `http://127.0.0.1:8000`, so the backend **must** run on port 8000.

```bash
cd backend

# 1a. Create your .env from the example
cp .env.example .env
```

Open `.env` and set the values below (see the table in section 5). At minimum you need
`DATABASE_URL` and `OPENAI_API_KEY`.

```bash
# 1b. Install Python dependencies
uv sync

# 1c. Install the Playwright browser (needed for follower scraping)
uv run playwright install chromium

# 1d. Start the API
uv run uvicorn app.main:app --reload --port 8000
```

On startup the app **auto-creates all database tables** (`init_db()` runs
`Base.metadata.create_all`). No separate migration step is needed for a fresh database.

- Backend: **http://127.0.0.1:8000**
- API docs (Swagger): **http://127.0.0.1:8000/docs**
- Health check: **http://127.0.0.1:8000/health** → `{"status": "healthy", ...}`

### Database constraint for the accept → conversation bridge

The outreach queue has a uniqueness guard on `(contact_id, purpose)` that prevents the
same person being double-queued.

- **Fresh database:** created automatically by `init_db()` — nothing to do.
- **Existing database** (tables already created before this feature): `create_all` will
  **not** add the constraint to an existing table, so run this once in the Supabase SQL
  editor:

  ```sql
  -- Must return ZERO rows first; resolve any duplicates before adding the constraint.
  SELECT contact_id, purpose, count(*)
  FROM outreach_queue
  GROUP BY contact_id, purpose
  HAVING count(*) > 1;

  ALTER TABLE outreach_queue
    ADD CONSTRAINT uq_outreach_contact_purpose UNIQUE (contact_id, purpose);
  ```

---

## 2. LinkedIn session (one-time, required for follower scanning)

The follower scan drives a real browser with your saved LinkedIn cookies. Authenticate once:

```bash
cd backend
uv run python test_auth.py
```

A Chrome window opens. Log in to LinkedIn manually (complete any 2FA), wait until you see
your feed, then press Enter in the terminal. Your session is saved to
`playwright-data/cookies.json` and reused by the app.

> The accept → conversation **bridge** (section 4) does **not** need this — it only reads
> the database and calls OpenAI. Only the follower **scan** drives a browser.

---

## 3. Frontend (React + Vite — port **5173**)

> Must run on port **5173** — it's the only origin the backend's CORS allows.

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

Open **http://localhost:5173**. If Vite reports a different port, free up 5173 and
restart, or API calls will be blocked by CORS.

---

## 4. The follower → conversation workflow

This is the core flow: turn followers who are **not** connections into conversations.

1. **Scan** — Followers page → **New Scan** tab → **Scan Followers**.
   A browser scrolls your followers. Only people who are **not already connected**
   (degree badge `2nd`/`3rd`) become candidates; `1st`-degree are excluded, anyone you
   already track is skipped, and any card with an unreadable badge is reported as an
   error (never silently included). The summary panel shows all of these counts.

2. **Generate notes** — select candidates → **Generate Notes** → review/edit the
   AI-written connection notes.

3. **Send & track** — use **Copy & Open Profile** to send the request on LinkedIn, mark
   each as sent, then **Save & Track**. Tracked requests appear under **Past Requests**
   as `pending`.

4. **Bridge accepted requests** — Followers page → **Past Requests** tab →
   **Check Acceptances**. For every request whose person now appears in your contacts,
   the status walks `pending → accepted → conversation_queued`, and a **first-touch
   message draft** is generated and added to the outreach queue. The banner reports how
   many conversations were queued.

5. **Review drafts** — open the **Queue** page to review, edit, and approve the generated
   first-touch drafts.

Connection-request status progression:

```
pending → accepted → conversation_queued        (happy path)
        ↘ already_connected | already_pending | failed | rejected | withdrawn
```

---

## 5. Environment variables (backend `.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Supabase Postgres connection string (`postgresql+asyncpg://...`). Use the Transaction pooler URI. |
| `OPENAI_API_KEY` | ✅ | OpenAI key for AI message/note generation (gpt-4o). |
| `SECRET_KEY` | ✅ | Any random string. |
| `APP_ENV` | — | `development` (default) or `production`. |
| `LINKEDIN_PROFILE_URL` | — | Your own profile URL; helps filter you out of follower scans. |
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | — | Optional; the app normally uses saved cookies (section 2). |
| `PERSONA_NAME` | — | Name used in generated messages (default "Cristina Rodriguez"). |
| `PERSONA_TITLE` | — | e.g. "Tech Professional". |
| `PERSONA_LOCATION` | — | e.g. "Seattle". |
| `PERSONA_BIO` | — | Short bio used as context. |
| `PERSONA_INTERESTS` | — | Comma-separated interests. |
| `PERSONA_TONE` | — | Tone for generated messages. |
| `RATE_LIMIT_MESSAGES_PER_DAY` | — | Daily send cap (default 50). |
| `RATE_LIMIT_PROFILES_PER_DAY` | — | Daily profile-enrichment cap (default 100). |

---

## 6. Quick verification

1. Backend: `curl -s http://127.0.0.1:8000/health` → `{"status":"healthy",...}`
2. Frontend: open http://localhost:5173 — the dashboard loads.
3. Bridge smoke test (no LinkedIn needed): seed one accepted request in the DB, then
   click **Past Requests → Check Acceptances** and confirm a draft appears on the
   **Queue** page.
