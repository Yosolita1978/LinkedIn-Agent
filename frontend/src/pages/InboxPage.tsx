import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchInbox, fetchConversation, syncInbox, fetchInboxStats } from "../api/inbox";
import type { InboxConversation, InboxMessage, InboxStats } from "../api/inbox";
import WarmthBadge from "../components/WarmthBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

const FILTER_TABS = [
  { key: "all", label: "All" },
  { key: "needs_reply", label: "Needs Reply" },
  { key: "waiting", label: "Waiting for Them" },
];

export default function InboxPage() {
  const [conversations, setConversations] = useState<InboxConversation[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  // Conversation detail state
  const [selectedContactId, setSelectedContactId] = useState<string | null>(null);
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  function loadData() {
    setLoading(true);
    setError(null);

    const filterParam = activeFilter === "all" ? undefined : activeFilter;

    Promise.all([fetchInbox(filterParam), fetchInboxStats()])
      .then(([inboxData, statsData]) => {
        setConversations(inboxData.conversations);
        setTotal(inboxData.total);
        setStats(statsData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, [activeFilter]);

  function handleSync() {
    setSyncing(true);
    setSyncResult(null);
    setError(null);

    syncInbox()
      .then((result) => {
        setSyncResult(
          `Synced ${result.conversations_synced} conversations, ${result.new_messages} new messages`
        );
        loadData();
      })
      .catch((err) => setError(err.message))
      .finally(() => setSyncing(false));
  }

  function handleSelectConversation(contactId: string) {
    setSelectedContactId(contactId);
    setMessagesLoading(true);

    fetchConversation(contactId)
      .then((data) => setMessages(data.messages))
      .catch((err) => setError(err.message))
      .finally(() => setMessagesLoading(false));
  }

  const selectedConversation = conversations.find(
    (c) => c.contact_id === selectedContactId
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Inbox</h1>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 flex items-center gap-2"
        >
          {syncing ? (
            <>
              <div className="w-4 h-4 animate-spin rounded-full border-2 border-blue-300 border-t-white" />
              Syncing...
            </>
          ) : (
            "Sync Now"
          )}
        </button>
      </div>

      {syncResult && (
        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
          <p className="text-sm text-green-400">{syncResult}</p>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="flex gap-3 mb-4">
          <div className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center">
            <p className="text-lg font-bold text-white">{stats.total_conversations}</p>
            <p className="text-xs text-slate-500">Conversations</p>
          </div>
          <div className={`px-3 py-1.5 border rounded-lg text-center ${
            stats.needs_reply > 0 ? "bg-amber-500/10 border-amber-500/30" : "bg-slate-800 border-slate-700"
          }`}>
            <p className={`text-lg font-bold ${stats.needs_reply > 0 ? "text-amber-400" : "text-white"}`}>
              {stats.needs_reply}
            </p>
            <p className="text-xs text-slate-500">Needs Reply</p>
          </div>
          <div className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center">
            <p className="text-lg font-bold text-white">{stats.waiting_for_them}</p>
            <p className="text-xs text-slate-500">Waiting</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveFilter(tab.key); setSelectedContactId(null); }}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeFilter === tab.key
                ? "bg-slate-700 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
            {tab.key === "needs_reply" && stats && stats.needs_reply > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full">
                {stats.needs_reply}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <ErrorMessage message={error} onRetry={loadData} />}
      {loading && <LoadingSpinner />}

      {!loading && !error && conversations.length === 0 && (
        <EmptyState
          title="No conversations"
          description={
            activeFilter !== "all"
              ? `No conversations matching "${activeFilter.replace("_", " ")}"`
              : "Click 'Sync Now' to fetch your LinkedIn conversations"
          }
        />
      )}

      {!loading && !error && conversations.length > 0 && (
        <div className="flex gap-4" style={{ minHeight: "60vh" }}>
          {/* Conversation list — left panel */}
          <div className="w-96 shrink-0 space-y-1 overflow-y-auto" style={{ maxHeight: "70vh" }}>
            <p className="text-xs text-slate-500 mb-2">{total} conversation(s)</p>
            {conversations.map((conv) => (
              <button
                key={conv.contact_id}
                onClick={() => handleSelectConversation(conv.contact_id)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedContactId === conv.contact_id
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-slate-700 bg-slate-800 hover:bg-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">
                        {conv.contact_name}
                      </span>
                      {conv.needs_reply && (
                        <span className="px-1.5 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full shrink-0">
                          Reply
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 truncate">
                      {conv.contact_company || conv.contact_headline || ""}
                    </p>
                    {conv.last_message_preview && (
                      <p className="text-xs text-slate-400 mt-1 truncate">
                        {conv.last_message_direction === "sent" ? "You: " : ""}
                        {conv.last_message_preview}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <WarmthBadge score={conv.warmth_score} size="sm" />
                    {conv.last_message_date && (
                      <p className="text-xs text-slate-600 mt-1">
                        {new Date(conv.last_message_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Message thread — right panel */}
          <div className="flex-1 bg-slate-800 rounded-lg border border-slate-700 p-4 overflow-y-auto" style={{ maxHeight: "70vh" }}>
            {!selectedContactId && (
              <div className="flex items-center justify-center h-full">
                <p className="text-slate-500 text-sm">Select a conversation to view messages</p>
              </div>
            )}

            {selectedContactId && messagesLoading && <LoadingSpinner />}

            {selectedContactId && !messagesLoading && (
              <div>
                {/* Thread header */}
                {selectedConversation && (
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-700">
                    <div>
                      <Link
                        to={`/contacts/${selectedConversation.contact_id}`}
                        className="text-lg font-medium text-blue-400 hover:text-blue-300"
                      >
                        {selectedConversation.contact_name}
                      </Link>
                      <p className="text-xs text-slate-500">
                        {selectedConversation.contact_company || selectedConversation.contact_headline || ""}
                        {" — "}
                        {selectedConversation.total_messages} messages
                      </p>
                    </div>
                    {selectedConversation.contact_linkedin_url && (
                      <a
                        href={selectedConversation.contact_linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-500"
                      >
                        Open LinkedIn
                      </a>
                    )}
                  </div>
                )}

                {/* Messages */}
                {messages.length === 0 ? (
                  <p className="text-sm text-slate-500">No messages found for this contact.</p>
                ) : (
                  <div className="space-y-3">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.direction === "sent" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[75%] p-3 rounded-lg text-sm ${
                            msg.direction === "sent"
                              ? "bg-blue-600/20 text-blue-100 rounded-br-sm"
                              : "bg-slate-700 text-slate-200 rounded-bl-sm"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.content || "(no content)"}</p>
                          <p className={`text-xs mt-1 ${
                            msg.direction === "sent" ? "text-blue-400/60" : "text-slate-500"
                          }`}>
                            {new Date(msg.date).toLocaleDateString()}{" "}
                            {new Date(msg.date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
