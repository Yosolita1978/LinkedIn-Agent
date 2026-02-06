import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchQueueItems, fetchQueueStats, updateQueueStatus, updateQueueMessage, deleteQueueItem } from "../api/queue";
import type { QueueItem, QueueStats } from "../types";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

const STATUS_TABS = ["all", "draft", "approved", "sent", "responded"];

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  function loadData() {
    setLoading(true);
    setError(null);

    const statusFilter = activeTab === "all" ? undefined : activeTab;

    Promise.all([fetchQueueItems(statusFilter), fetchQueueStats()])
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

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Outreach Queue</h1>

      {/* Stats */}
      {stats && (
        <div className="flex gap-3 mb-4">
          {STATUS_TABS.filter(t => t !== "all").map((status) => (
            <div key={status} className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center">
              <p className="text-lg font-bold text-white">{stats.by_status[status] ?? 0}</p>
              <p className="text-xs text-slate-500 capitalize">{status}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
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

      {error && <ErrorMessage message={error} onRetry={loadData} />}
      {loading && <LoadingSpinner />}

      {!loading && !error && items.length === 0 && (
        <EmptyState title="No queue items" description={activeTab !== "all" ? `No items with status "${activeTab}"` : "Generate messages from the Contacts page to add items here"} />
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">{total} item(s)</p>
          {items.map((item) => (
            <div key={item.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <Link to={`/contacts/${item.contact_id}`} className="text-sm font-medium text-blue-400 hover:text-blue-300">
                    {item.contact_name}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {item.contact_company ?? ""} — {item.purpose} / {item.use_case}
                  </p>
                </div>
                <StatusBadge status={item.status} />
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
                      onClick={() => { setEditingId(item.id); setEditText(item.generated_message ?? ""); }}
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
