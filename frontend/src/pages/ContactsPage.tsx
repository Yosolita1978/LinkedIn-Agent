import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { fetchContacts } from "../api/contacts";
import type { Contact } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import SegmentBadge from "../components/SegmentBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [segment, setSegment] = useState("");
  const [sortBy, setSortBy] = useState("warmth");
  const [sortOrder, setSortOrder] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 30;
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [searchTrigger, setSearchTrigger] = useState(0);

  function loadContacts() {
    setLoading(true);
    setError(null);

    fetchContacts({
      page,
      page_size: pageSize,
      search: search || undefined,
      segment: segment || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    })
      .then((data) => {
        setContacts(data.contacts);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadContacts(); }, [page, segment, sortBy, sortOrder, searchTrigger]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      setSearchTrigger((n) => n + 1);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Contacts</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by name, company..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder-slate-500 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={segment}
          onChange={(e) => { setSegment(e.target.value); setPage(1); }}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200"
        >
          <option value="">All Segments</option>
          <option value="mujertech">MujerTech</option>
          <option value="cascadia">Cascadia AI</option>
          <option value="job_target">Job Target</option>
        </select>
        <select
          value={sortBy}
          onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200"
        >
          <option value="warmth">Sort by Warmth</option>
          <option value="name">Sort by Name</option>
          <option value="last_message">Sort by Last Message</option>
          <option value="total_messages">Sort by Total Messages</option>
        </select>
        <button
          onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:bg-slate-700"
        >
          {sortOrder === "desc" ? "Desc" : "Asc"}
        </button>
      </div>

      <p className="text-xs text-slate-500 mb-4">{total.toLocaleString()} contacts</p>

      {loading && <LoadingSpinner />}
      {error && <ErrorMessage message={error} onRetry={loadContacts} />}

      {!loading && !error && contacts.length === 0 && (
        <EmptyState title="No contacts found" description="Try a different search or filter" />
      )}

      {!loading && !error && contacts.length > 0 && (
        <>
          <div className="bg-slate-800 rounded-lg border border-slate-700 divide-y divide-slate-700">
            {contacts.map((contact) => (
              <Link
                key={contact.id}
                to={`/contacts/${contact.id}`}
                className="flex items-center justify-between p-4 hover:bg-slate-700/50"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-slate-200 truncate">{contact.name}</p>
                    {contact.segment_tags?.map((seg) => (
                      <SegmentBadge key={seg} segment={seg} />
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-0.5">
                    {[contact.position, contact.company].filter(Boolean).join(" at ") || contact.headline || ""}
                  </p>
                </div>
                <div className="flex items-center gap-4 shrink-0 ml-4">
                  {contact.total_messages > 0 && (
                    <span className="text-xs text-slate-500">{contact.total_messages} msgs</span>
                  )}
                  {contact.last_message_date && (
                    <span className="text-xs text-slate-500 hidden sm:inline">
                      {new Date(contact.last_message_date).toLocaleDateString()}
                    </span>
                  )}
                  <WarmthBadge score={contact.warmth_score} />
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-300 disabled:opacity-40 hover:bg-slate-700"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-300 disabled:opacity-40 hover:bg-slate-700"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
