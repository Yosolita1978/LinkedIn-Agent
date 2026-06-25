import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listConnectionRequests } from "../api/followers";
import { fetchQueueItems } from "../api/queue";
import { fetchOpportunities } from "../api/resurrection";
import type { ConnectionRequestRecord, QueueItem } from "../types";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadData() {
    setLoading(true);
    setError(null);
    Promise.all([
      listConnectionRequests(),
      fetchQueueItems("draft", undefined, 100, 0),
      fetchOpportunities(),
    ])
      .then(([reqData, draftData, oppData]) => {
        setRequests(reqData.requests);
        setDrafts(draftData.items);
        setOppCount(oppData.count);
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

  // Conversion funnel. Candidate / Sent / Responded are NOT derivable from the
  // current API (candidates aren't persisted; queue stats aren't source-filtered),
  // so they render as explicit "not available yet" stages — never faked.
  const funnelStages: FunnelStage[] = [
    { label: "Candidate", count: null },
    { label: "Requested", count: requestedCount },
    { label: "Accepted", count: acceptedCount },
    { label: "Drafted", count: draftedCount },
    { label: "Sent", count: null },
    { label: "Responded", count: null, emphasis: true },
  ];

  const firstTouchDrafts = drafts.filter(isFirstTouch);

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

      {/* 1. Header strip — two honest numbers + a pending weekly-cap slot */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <HeaderStat value={String(requestsSentThisWeek)} label="Requests sent this week" />
        <HeaderStat
          value={String(draftedCount)}
          label="Conversations started"
          caption="all time · weekly metric pending"
        />
        {/* TODO(weekly-cap): the weekly invitation cap isn't implemented yet.
            Render the slot but never a fabricated number. */}
        <HeaderStat value="— / —" label="Weekly cap" caption="cap not set yet" pending />
      </div>

      {/* 2. Conversion funnel — the hero */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Conversion funnel</h2>
        <Funnel stages={funnelStages} />
      </section>

      {/* 3. Drafts to approve — the highest-value action */}
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

      {/* 4. Candidates to request — no persisted candidate store yet, so this is
          an honest CTA into the scan flow, not fabricated rows. */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Candidates to request</h2>
        <EmptyState
          title="Find non-connection followers to request"
          description="Candidates aren't stored between scans yet. Run a scan to find followers who aren't connected and send requests."
          action={
            <Link
              to="/followers"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500"
            >
              Go to Followers to Convert
            </Link>
          }
        />
      </section>

      {/* 5. Reactivate strip */}
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
