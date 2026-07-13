import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listConnectionRequests, getConnectionRequestStats, fetchCandidates } from "../api/followers";
import { fetchQueueItems, fetchQueueStats } from "../api/queue";
import { fetchOpportunities } from "../api/resurrection";
import { fetchSettings, updateSettings } from "../api/settings";
import type {
  ConnectionRequestRecord,
  QueueItem,
  QueueStats,
  ConnectionRequestStatsResponse,
} from "../types";
import Funnel, { type FunnelStage } from "../components/Funnel";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

// Connection-request statuses that represent an invitation that was actually
// sent (i.e. not a failed/already-* outcome).
const SENT_REQUEST_STATUSES = ["pending", "accepted", "conversation_queued"];
const ACCEPTED_STATUSES = ["accepted", "conversation_queued"];

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

// A queue item is a follower first-touch draft when the accept→conversation
// bridge created it (outreach_type "warm", purpose "introduce").
function isFirstTouch(item: QueueItem): boolean {
  return item.outreach_type === "warm" && item.purpose === "introduce";
}

export default function DashboardPage() {
  const [requests, setRequests] = useState<ConnectionRequestRecord[]>([]);
  const [drafts, setDrafts] = useState<QueueItem[]>([]);
  const [oppCount, setOppCount] = useState(0);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [connStats, setConnStats] = useState<ConnectionRequestStatsResponse | null>(null);
  const [weeklyCap, setWeeklyCap] = useState<number | null>(null);
  const [newCandidateCount, setNewCandidateCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadData() {
    setLoading(true);
    setError(null);
    Promise.all([
      listConnectionRequests(),
      fetchQueueItems("draft", undefined, 100, 0),
      fetchOpportunities(),
      fetchQueueStats(),
      getConnectionRequestStats(),
      fetchSettings(),
      fetchCandidates("new", 1, 0),
    ])
      .then(([reqData, draftData, oppData, qStats, cStats, settings, backlog]) => {
        setRequests(reqData.requests);
        setDrafts(draftData.items);
        setOppCount(oppData.count);
        setQueueStats(qStats);
        setConnStats(cStats);
        setWeeklyCap(settings.weekly_request_cap);
        setNewCandidateCount(backlog.counts["new"] ?? 0);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  // ── Derived counts (all real, from the connection-request records) ──
  const cutoff = Date.now() - WEEK_MS;
  const requestsSentThisWeek = requests.filter(
    (r) => new Date(r.sent_at).getTime() >= cutoff,
  ).length;

  const requestedCount = requests.filter((r) => SENT_REQUEST_STATUSES.includes(r.status)).length;
  const acceptedCount = requests.filter((r) => ACCEPTED_STATUSES.includes(r.status)).length;
  const draftedCount = requests.filter((r) => r.status === "conversation_queued").length;

  // Sent / Responded now come from real queue status counts.
  const sentCount = queueStats?.by_status["sent"] ?? 0;
  const respondedCount = queueStats?.by_status["responded"] ?? 0;

  // Conversion funnel. Every stage is now backed by real data, so there are no
  // "not available yet" placeholders. (Candidate was dropped — no persisted
  // candidate store exists, and an empty stage was just noise.)
  const funnelStages: FunnelStage[] = [
    { label: "Requested", count: requestedCount },
    { label: "Accepted", count: acceptedCount },
    { label: "Drafted", count: draftedCount },
    { label: "Sent", count: sentCount },
    { label: "Responded", count: respondedCount, emphasis: true },
  ];

  const firstTouchDrafts = drafts.filter(isFirstTouch);

  // Segments with at least one request sent, sorted by acceptance rate.
  const segmentRows = (connStats?.by_segment ?? [])
    .filter((s) => s.total_sent > 0)
    .sort((a, b) => b.acceptance_rate - a.acceptance_rate);

  async function handleSaveCap(next: number) {
    // Optimistic: show the new cap immediately, persist in the background.
    setWeeklyCap(next);
    try {
      const saved = await updateSettings({ weekly_request_cap: next });
      setWeeklyCap(saved.weekly_request_cap);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save weekly cap");
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-white mb-6">Today</h1>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-white">Today</h1>

      {error && <ErrorMessage message={error} onRetry={loadData} />}

      {/* 1. Header strip — three real numbers, no dead slot */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <WeeklyCapCard
          sent={requestsSentThisWeek}
          cap={weeklyCap}
          onSave={handleSaveCap}
        />
        <HeaderStat
          value={String(draftedCount)}
          label="Conversations started"
          caption="follower requests that reached a draft"
        />
        <AcceptanceCard stats={connStats} />
      </div>

      {/* 2. Conversion funnel — the hero, now all real */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Conversion funnel</h2>
        <Funnel stages={funnelStages} />
        <p className="text-[11px] text-slate-600 mt-2">
          Requested–Drafted track follower conversions. Sent &amp; Responded count
          all outreach (including reconnects), so they may include non-follower contacts.
        </p>
      </section>

      {/* 3. Acceptance by segment — which segments are actually converting */}
      {segmentRows.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Acceptance by segment</h2>
          <div className="bg-slate-800 rounded-lg border border-slate-700 divide-y divide-slate-700">
            {segmentRows.map((s) => (
              <div key={s.segment} className="flex items-center gap-4 p-3">
                <span className="text-sm text-white capitalize w-28 shrink-0">{s.segment}</span>
                <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${Math.min(100, s.acceptance_rate)}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-emerald-400 w-12 text-right">
                  {s.acceptance_rate}%
                </span>
                <span className="text-xs text-slate-500 w-24 text-right">
                  {s.accepted}/{s.total_sent} accepted
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 4. Drafts to approve — the highest-value action */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300">
            Drafts to approve
            {firstTouchDrafts.length > 0 && (
              <span className="ml-2 text-xs font-normal text-emerald-400">
                {firstTouchDrafts.length} waiting
              </span>
            )}
          </h2>
          <Link to="/queue" className="text-xs text-blue-400 hover:text-blue-300">
            Open Conversations →
          </Link>
        </div>

        {firstTouchDrafts.length === 0 ? (
          <EmptyState
            title="No first-touch drafts waiting"
            description="When a follower accepts your request, their generated first message will appear here for approval."
          />
        ) : (
          <div className="space-y-2">
            {firstTouchDrafts.map((item) => (
              <div key={item.id} className="bg-slate-800 rounded-lg border border-emerald-500/30 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      to={`/contacts/${item.contact_id}`}
                      className="text-sm font-medium text-blue-400 hover:text-blue-300"
                    >
                      {item.contact_name}
                    </Link>
                    {item.contact_company && (
                      <p className="text-xs text-slate-500">{item.contact_company}</p>
                    )}
                    {item.generated_message && (
                      <p className="text-sm text-slate-300 mt-2 line-clamp-2">
                        {item.generated_message}
                      </p>
                    )}
                  </div>
                  <Link
                    to="/queue"
                    className="shrink-0 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500"
                  >
                    Review &amp; approve
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 5. Candidates to request — no persisted candidate store yet, so this is
          an honest CTA into the scan flow, not fabricated rows. */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Candidates to request</h2>
        {newCandidateCount > 0 ? (
          <Link
            to="/followers"
            className="flex items-center justify-between bg-slate-800 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-white">
                {newCandidateCount} {newCandidateCount === 1 ? "person" : "people"} you follow waiting in your backlog
              </p>
              <p className="text-xs text-slate-500">Write notes and send requests, oldest scan first.</p>
            </div>
            <span className="text-blue-400 text-sm">Open Backlog →</span>
          </Link>
        ) : (
          <EmptyState
            title="Find people you follow to request"
            description="Your backlog is empty. Run a scan to find people you follow who aren't connected — they'll be saved here so you can work through them over time."
            action={
              <Link
                to="/followers"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500"
              >
                Go to People to Convert
              </Link>
            }
          />
        )}
      </section>

      {/* 6. Reactivate strip */}
      <section>
        <Link
          to="/opportunities"
          className="flex items-center justify-between bg-slate-800 rounded-lg border border-slate-700 p-4 hover:border-slate-600 transition-colors"
        >
          <div>
            <p className="text-sm font-medium text-white">Reactivate dormant conversations</p>
            <p className="text-xs text-slate-500">
              {oppCount} open {oppCount === 1 ? "opportunity" : "opportunities"}
            </p>
          </div>
          <span className="text-blue-400 text-sm">Open Reactivate →</span>
        </Link>
      </section>
    </div>
  );
}

// Weekly-cap progress meter with an inline, editable target.
function WeeklyCapCard({
  sent,
  cap,
  onSave,
}: {
  sent: number;
  cap: number | null;
  onSave: (next: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  function startEdit() {
    setDraft(cap ? String(cap) : "");
    setEditing(true);
  }

  function commit() {
    const next = parseInt(draft, 10);
    if (!Number.isNaN(next) && next >= 1 && next <= 1000) {
      onSave(next);
    }
    setEditing(false);
  }

  const pct = cap && cap > 0 ? Math.min(100, Math.round((sent / cap) * 100)) : 0;

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <div className="flex items-baseline gap-1">
        <p className="text-3xl font-bold text-white">{sent}</p>
        <span className="text-lg text-slate-500">/</span>
        {editing ? (
          <input
            type="number"
            min={1}
            max={1000}
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") setEditing(false);
            }}
            className="w-16 bg-slate-900 border border-blue-500 rounded px-1 text-lg font-bold text-white"
          />
        ) : (
          <button
            onClick={startEdit}
            className="text-lg font-bold text-slate-300 hover:text-blue-400"
            title="Click to set your weekly target"
          >
            {cap ?? "—"}
          </button>
        )}
      </div>
      <p className="text-sm text-slate-400 mt-1">Requests this week / cap</p>

      <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${pct >= 100 ? "bg-amber-500" : "bg-blue-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <button
        onClick={startEdit}
        className="text-[11px] text-slate-600 mt-1 hover:text-blue-400"
      >
        {cap ? "Edit weekly cap" : "Set a weekly cap"}
      </button>
    </div>
  );
}

// Overall acceptance-rate headline. Honest-empty until any request exists.
function AcceptanceCard({ stats }: { stats: ConnectionRequestStatsResponse | null }) {
  const hasData = stats !== null && stats.total_requests > 0;
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <p className={`text-3xl font-bold ${hasData ? "text-emerald-400" : "text-slate-600"}`}>
        {hasData ? `${stats.overall_acceptance_rate}%` : "—"}
      </p>
      <p className="text-sm text-slate-400 mt-1">Acceptance rate</p>
      <p className="text-[11px] text-slate-600 mt-0.5">
        {hasData
          ? `${stats.total_accepted} of ${stats.total_requests} accepted`
          : "no requests sent yet"}
      </p>
    </div>
  );
}

function HeaderStat({
  value,
  label,
  caption,
  pending,
}: {
  value: string;
  label: string;
  caption?: string;
  pending?: boolean;
}) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <p className={`text-3xl font-bold ${pending ? "text-slate-600" : "text-white"}`}>
        {value}
      </p>
      <p className="text-sm text-slate-400 mt-1">{label}</p>
      {caption && <p className="text-[11px] text-slate-600 mt-0.5">{caption}</p>}
    </div>
  );
}
