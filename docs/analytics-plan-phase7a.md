# Analytics Plan — Phase 7a

**Date:** 2026-02-10
**Status:** Planned

---

## Data Source Ground Rules

| Data Source | Type | Refreshes |
|---|---|---|
| **LinkedIn export** (Connections.csv, messages.csv) | Historical snapshot | Manual re-import (monthly at most) |
| **Queue table** (outreach items) | Live | Every action through the app |
| **Followers flow** (connection requests) | Live (needs logging) | Every scan/connect action |
| **Warmth / Resurrection / Segments** | Computed | On-demand recalculation from imported data |

---

## Module 1: Network Overview (snapshot)

**Source:** Contacts table + Segments

- Total contacts, unique companies, segment distribution
- Warmth distribution (hot/warm/cool/cold buckets with counts)
- Average warmth by segment (mujertech vs cascadia vs job_target vs untagged)
- Top 10 companies by contact count ("where is your network concentrated?")
- Network archetype classification (Thought Leader / Insider / Connector / Climber / Builder — computed from company diversity, title density, senior contact %)

**Why it matters:** This is the "at a glance" view. You see it once and it tells you the shape of your network. Refresh when you re-import LinkedIn data.

**Endpoint:** `GET /api/analytics/overview`

---

## Module 2: Relationship Health (snapshot + alerts)

**Source:** Contacts table (warmth_score, last_message_date, warmth_breakdown)

- **Decay alerts**: Contacts with warmth 40-70 and no message in 30+ days — going cold soon
- **Critical list**: Top 10 contacts with highest warmth but oldest last_message_date (most at risk)
- **Warmth breakdown averages**: Which component is weakest across your network? (recency? depth? initiation?)
- **Stale connections**: Contacts connected 1+ years ago with zero messages (never activated)

**Why it matters:** The article's core thesis — see who's going cold before it's too late. This is your "invest this week" list.

**Endpoint:** `GET /api/analytics/health`

---

## Module 3: Outreach Funnel (live, ongoing)

**Source:** Queue table (timestamps on each status transition)

- **Pipeline counts**: How many items in draft / approved / sent / responded right now
- **Conversion rates**: draft→approved %, approved→sent %, sent→responded %
- **Response rate by segment**: Do cascadia contacts respond more than mujertech?
- **Response rate by purpose**: Does "reconnect" get more replies than "invite_community"?
- **Response rate by outreach_type**: resurrection vs warm vs cold
- **Avg time in status**: How long do drafts sit before you approve them?
- **Weekly outreach volume**: Items moved to "sent" per week (tracked from sent_at timestamps)

**Why it matters:** This tells you if your outreach strategy is actually working. It gets richer over time as more items flow through the queue.

**Endpoint:** `GET /api/analytics/funnel`

---

## Module 4: Message Intelligence (snapshot)

**Source:** Message table (direction, content_length, is_substantive, date)

- Total messages sent vs received (lifetime from export)
- Substantive vs shallow ratio (% of messages flagged is_substantive)
- Average message depth by warmth bucket (do hot contacts have deeper conversations?)
- Communication balance: network-wide initiation ratio (are you mostly initiating, or mostly responding?)
- Top 10 deepest conversations (total messages + highest substantive ratio)
- Message depth distribution (histogram of content_length across all messages)

**Why it matters:** Understand your communication patterns. Are you writing meaningful messages or just "congrats!" and "thanks!"? This is a one-time insight from the export, not ongoing tracking.

**Endpoint:** `GET /api/analytics/messages`

---

## Module 5: Resurrection Dashboard (snapshot + live conversion)

**Source:** ResurrectionOpportunity table + Queue table

- **Total opportunities** by hook type (they_waiting, promise_made, question_unanswered, dormant)
- **By warmth bucket**: High-warmth resurrection opportunities (biggest bang for the effort)
- **Age distribution**: How old are these opportunities? (detected_at vs today)
- **Conversion funnel** (live): resurrection opportunity → queued as draft → sent → responded

**Why it matters:** You have 317 opportunities. This module helps you prioritize them and track whether acting on them actually leads to responses.

**Endpoint:** `GET /api/analytics/resurrection`

---

## Deferred to Phase 7b

| Feature | Reason |
|---|---|
| Reciprocity ledger | Needs endorsement/recommendation CSV imports |
| Full vouch score | Needs endorsement + recommendation data |
| Warm path discovery | Needs second-degree connection logic (complex) |
| Live message tracking | Can't auto-sync with LinkedIn; only tracks what goes through our app |

---

## Frontend

The `DashboardPage.tsx` gets rebuilt with 5 cards/sections, one per module. Snapshot data loads on page open. Live funnel data updates as you use the app.
