# TODO / Follow-ups

Living list of known follow-ups. Most of these were surfaced while refocusing the
app around the **followers → connection → conversation** funnel.

## Frontend

- [ ] **Regenerate-with-AI on connection notes (Followers to Convert).**
  The first-touch queue messages already have a per-item "Regenerate with AI"
  button on the **Conversations** page. The connection **notes** generated on
  *Followers to Convert* (via `POST /api/followers/generate-notes`) are also
  AI-written, but currently can only be edited manually — there's no regenerate
  affordance. Add the same "type an instruction → regenerate" flow to each note.
  - Caveat: `generate-notes` regenerates **all** candidates at once. A clean
    per-note regenerate likely needs a single-candidate note endpoint (or a
    client-side single-candidate call to the same endpoint).

- [ ] **Delete now-orphaned modules** left after the dashboard redesign (unused,
  harmless, build still passes):
  - `frontend/src/api/ranking.ts` (`fetchRecommendations`)
  - `frontend/src/components/PriorityBadge.tsx`
  - `frontend/src/api/analytics.ts` (`fetchNetworkOverview`)
  - `frontend/src/api/contacts.ts` → `fetchTopWarmth` (rest of module still used)

## Backend (needed by the redesigned dashboard)

These are the gaps that force "not available yet" states on the Today / Reactivate
funnels. Until they exist, the UI shows honest unavailable states instead of faking
numbers.

- [ ] **Source-filtered queue stats** (counts by `outreach_type` / `purpose`).
  Unblocks the funnel **Sent** and **Responded** stages on both funnels — today
  queue stats lump first-touch, reactivation, and job-search together.
- [ ] **Persisted follower candidates** (a store + count). Scans are currently
  ephemeral, so the funnel **Candidate** stage and the Today "Candidates to
  request" work queue have no backing data.
- [ ] **`conversation_queued_at` timestamp** on `connection_request` (or a
  weekly-metrics endpoint) → the Today header's "conversations started **this
  week**" (currently shown all-time).
- [ ] **Weekly invitation cap** (value + usage). Fills the Today header cap slot,
  and is the gate marked `TODO(weekly-cap)` in
  `follower_connector.connect_with_candidates` (the request-sending path).
- [ ] **Settings / config API** (persona, rate limits, upload). Needed to build
  the Settings utility page (omitted from nav until this exists).
- [ ] **Candidate prioritization / warmth** for non-contact followers, so
  *Followers to Convert* can sort by true priority instead of segment-presence.

## Out of scope for now (parked)

- [ ] Conversation-reactivation automation (beyond the current manual flow).
- [ ] Campaign sequences (multi-step follow-ups / drip).
