import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchQueueItems, fetchQueueStats, updateQueueStatus, updateQueueMessage, regenerateQueueMessage, deleteQueueItem } from "../api/queue";
import type { QueueItem, QueueStats } from "../types";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

const STATUS_TABS = ["all", "draft", "approved", "sent", "responded"];

// The queue is now fed by multiple sources. We derive each item's source from
// the fields the backend already sets, then filter client-side. (The API can't
// filter by source server-side yet — see backend follow-ups.)
const SOURCE_OPTIONS = [
  { value: "all", label: "All sources" },
  { value: "first-touch", label: "First-touch (followers)" },
  { value: "reactivation", label: "Reactivation" },
  { value: "job-search", label: "Job search" },
];

function itemSource(item: QueueItem): string {
  if (item.outreach_type === "resurrection") return "reactivation";
  if (item.outreach_type === "warm" && item.purpose === "introduce") return "first-touch";
  if (item.use_case === "job_search" || item.use_case === "job_target") return "job-search";
  return "other";
}

// The most recent thing that happened on an item (created / approved / sent /
// replied). Sorting by this ascending surfaces the conversations that have been
// quiet the longest — the ones most in need of a re-connect.
function lastActivity(item: QueueItem): number {
  const stamps = [item.created_at, item.approved_at, item.sent_at, item.replied_at]
    .filter((t): t is string => Boolean(t))
    .map((t) => new Date(t).getTime());
  return stamps.length ? Math.max(...stamps) : 0;
}

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [activeTab, setActiveTab] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Regenerate state — a per-item "improve with AI" panel
  const [regenOpenId, setRegenOpenId] = useState<string | null>(null);
  const [regenInstruction, setRegenInstruction] = useState("");
  const [regenLoading, setRegenLoading] = useState(false);

  function loadData() {
    setLoading(true);
    setError(null);

    const statusFilter = activeTab === "all" ? undefined : activeTab;

    // Fetch a generous page (100 = the API max) so the client-side source
    // filter is meaningful.
    Promise.all([fetchQueueItems(statusFilter, undefined, 100, 0), fetchQueueStats()])
      .then(([listData, statsData]) => {
        setItems(listData.items);
        setTotal(listData.total);
        setStats(statsData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, [activeTab]);

  async function handleStatusChange(itemId: string, newStatus: string) {
    setActionLoading(itemId);
    try {
      await updateQueueStatus(itemId, newStatus);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleSaveMessage(itemId: string) {
    setActionLoading(itemId);
    try {
      await updateQueueMessage(itemId, editText);
      setEditingId(null);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDelete(itemId: string) {
    setActionLoading(itemId);
    try {
      await deleteQueueItem(itemId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRegenerate(itemId: string) {
    setRegenLoading(true);
    setError(null);
    try {
      // Message edits require draft status. If the item was approved, revert it
      // to draft first so the regenerated message can be saved (and re-reviewed).
      const item = items.find((i) => i.id === itemId);
      if (item && item.status === "approved") {
        await updateQueueStatus(itemId, "draft");
      }
      // Generate a new version using the user's instruction, persist it, then
      // reconcile to server state so the new draft shows in place.
      const data = await regenerateQueueMessage(itemId, regenInstruction || undefined);
      await updateQueueMessage(itemId, data.message);
      setRegenOpenId(null);
      setRegenInstruction("");
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regeneration failed");
      // The status may have changed (e.g. reverted to draft) before the failure —
      // reconcile to the real server state rather than showing stale data.
      loadData();
    } finally {
      setRegenLoading(false);
    }
  }

  // Stalest first: surface the conversations whose last activity was longest
  // ago, so you're prompted to re-connect instead of forgetting them.
  const visibleItems = (
    sourceFilter === "all" ? items : items.filter((i) => itemSource(i) === sourceFilter)
  )
    .slice()
    .sort((a, b) => lastActivity(a) - lastActivity(b));

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Conversations</h1>

      {/* Stats */}
      {stats && (
        <div className="flex flex-wrap gap-3 mb-4">
          {STATUS_TABS.filter(t => t !== "all").map((status) => (
            <div key={status} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center">
              <p className="text-lg font-bold text-white">{stats.by_status[status] ?? 0}</p>
              <p className="text-xs text-slate-500 capitalize">{status}</p>
            </div>
          ))}
          <div className={`px-3 py-1.5 border rounded-lg text-center ${
            stats.remaining_today === 0
              ? "bg-red-500/10 border-red-500/30"
              : stats.remaining_today <= 10
                ? "bg-amber-500/10 border-amber-500/30"
                : "bg-slate-800 border-slate-700"
          }`}>
            <p className={`text-lg font-bold ${
              stats.remaining_today === 0
                ? "text-red-400"
                : stats.remaining_today <= 10
                  ? "text-amber-400"
                  : "text-white"
            }`}>
              {stats.sent_today}/{stats.daily_limit}
            </p>
            <p className="text-xs text-slate-500">Sent Today</p>
          </div>
        </div>
      )}

      {/* Filters: status tabs + source dropdown */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md capitalize transition-colors ${
                activeTab === tab
                  ? "bg-slate-700 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {SOURCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadData} />}
      {loading && <LoadingSpinner />}

      {!loading && !error && visibleItems.length === 0 && (
        <EmptyState
          title="No conversations here"
          description={
            sourceFilter !== "all"
              ? `No ${SOURCE_OPTIONS.find((o) => o.value === sourceFilter)?.label.toLowerCase()} items${activeTab !== "all" ? ` with status "${activeTab}"` : ""}.`
              : activeTab !== "all"
                ? `No items with status "${activeTab}".`
                : "Drafts appear here when a follower accepts (first-touch) or when you queue a reactivation message."
          }
        />
      )}

      {!loading && !error && visibleItems.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            {visibleItems.length} item(s){sourceFilter === "all" && total !== items.length ? ` of ${total}` : ""} · least recent activity first
          </p>
          {visibleItems.map((item) => (
            <div key={item.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <Link to={`/contacts/${item.contact_id}`} className="text-sm font-medium text-blue-400 hover:text-blue-300">
                      {item.contact_name}
                    </Link>
                    {item.contact_linkedin_url && (
                      <a
                        href={item.contact_linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-400"
                        title="Open LinkedIn profile"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                        </svg>
                      </a>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {item.contact_company ?? ""} — {item.purpose} / {item.use_case}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <StatusBadge status={item.status} />
                  <SourceTag source={itemSource(item)} />
                </div>
              </div>

              {/* Message */}
              {editingId === item.id ? (
                <div className="mt-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />

                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleSaveMessage(item.id)}
                      disabled={actionLoading === item.id}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1.5 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                item.generated_message && (
                  <p className="text-sm text-slate-300 mt-2 whitespace-pre-wrap bg-slate-700/50 rounded p-3">
                    {item.generated_message}
                  </p>
                )
              )}

              {/* Timestamps */}
              <div className="flex gap-4 mt-2 text-xs text-slate-500">
                <span>Created: {new Date(item.created_at).toLocaleDateString()}</span>
                {item.approved_at && <span>Approved: {new Date(item.approved_at).toLocaleDateString()}</span>}
                {item.sent_at && <span>Sent: {new Date(item.sent_at).toLocaleDateString()}</span>}
                {item.replied_at && <span>Replied: {new Date(item.replied_at).toLocaleDateString()}</span>}
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-3">
                {item.status === "draft" && (
                  <>
                    <button
                      onClick={() => { setRegenOpenId(regenOpenId === item.id ? null : item.id); setRegenInstruction(""); setEditingId(null); }}
                      className="px-3 py-1.5 text-sm border border-purple-500/40 text-purple-300 rounded-lg hover:bg-purple-500/10"
                    >
                      Regenerate with AI
                    </button>
                    <button
                      onClick={() => { setEditingId(item.id); setEditText(item.generated_message ?? ""); setRegenOpenId(null); }}
                      className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleStatusChange(item.id, "approved")}
                      disabled={actionLoading === item.id}
                      className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={actionLoading === item.id}
                      className="px-3 py-1.5 text-sm text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </>
                )}
                {item.status === "approved" && (
                  <>
                    <button
                      onClick={() => handleStatusChange(item.id, "sent")}
                      disabled={actionLoading === item.id}
                      className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50"
                    >
                      Mark Sent
                    </button>
                    <button
                      onClick={() => { setRegenOpenId(regenOpenId === item.id ? null : item.id); setRegenInstruction(""); setEditingId(null); }}
                      className="px-3 py-1.5 text-sm border border-purple-500/40 text-purple-300 rounded-lg hover:bg-purple-500/10"
                    >
                      Regenerate with AI
                    </button>
                    <button
                      onClick={() => handleStatusChange(item.id, "draft")}
                      disabled={actionLoading === item.id}
                      className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-50"
                    >
                      Back to Draft
                    </button>
                  </>
                )}
                {item.status === "sent" && (
                  <button
                    onClick={() => handleStatusChange(item.id, "responded")}
                    disabled={actionLoading === item.id}
                    className="px-3 py-1.5 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 disabled:opacity-50"
                  >
                    Mark Responded
                  </button>
                )}
              </div>

              {/* Regenerate-with-AI panel (drafts only — the message is editable) */}
              {regenOpenId === item.id && (
                <div className="mt-3 p-3 bg-slate-700/50 rounded-lg border border-purple-500/30">
                  <label className="block text-xs text-slate-400 mb-1">
                    Tell the AI what to change, then regenerate the message:
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={regenInstruction}
                      onChange={(e) => setRegenInstruction(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !regenLoading) handleRegenerate(item.id); }}
                      placeholder="e.g. mention Cascadia AI, make it shorter, less salesy, ask about their work"
                      className="flex-1 px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      onClick={() => handleRegenerate(item.id)}
                      disabled={regenLoading}
                      className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-500 disabled:opacity-50 whitespace-nowrap flex items-center gap-1.5"
                    >
                      {regenLoading ? (
                        <>
                          <div className="w-3 h-3 animate-spin rounded-full border-2 border-purple-300 border-t-white" />
                          Regenerating...
                        </>
                      ) : (
                        "Regenerate message"
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">
                    The regenerated version is saved as a draft for review. Regenerate again or edit manually.
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SourceTag({ source }: { source: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    "first-touch": { bg: "bg-blue-500/20", text: "text-blue-400", label: "First-touch" },
    reactivation: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Reactivation" },
    "job-search": { bg: "bg-purple-500/20", text: "text-purple-400", label: "Job search" },
    other: { bg: "bg-slate-700", text: "text-slate-400", label: "Other" },
  };
  const style = styles[source] ?? styles.other;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}
