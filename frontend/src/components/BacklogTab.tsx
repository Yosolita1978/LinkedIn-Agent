import { useEffect, useState, useCallback } from "react";
import { fetchCandidates, updateCandidate, generateNotes, trackConnectionRequests } from "../api/followers";
import type { BacklogCandidate, BacklogListResponse, FollowerCandidate } from "../types";
import SegmentBadge from "./SegmentBadge";
import ErrorMessage from "./ErrorMessage";

const STATUS_TABS = [
  { value: "new", label: "New" },
  { value: "noted", label: "Noted" },
  { value: "requested", label: "Requested" },
  { value: "skipped", label: "Skipped" },
];

const PAGE_SIZE = 20;

// Map a persisted backlog row to the shape the note generator + tracker expect.
function toFollowerCandidate(c: BacklogCandidate): FollowerCandidate {
  return {
    name: c.name,
    headline: c.headline ?? "",
    profile_url: c.profile_url,
    location: c.location ?? "",
    company: c.company ?? "",
    about: c.about ?? "",
    segments: c.segments ?? [],
  };
}

export default function BacklogTab() {
  const [status, setStatus] = useState("new");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<BacklogListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-card transient state
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchCandidates(status, PAGE_SIZE, offset)
      .then((d) => {
        setData(d);
        // Seed note drafts from saved notes so the textareas show stored text.
        const seeded: Record<string, string> = {};
        d.candidates.forEach((c) => { seeded[c.id] = c.note ?? ""; });
        setDrafts(seeded);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load backlog"))
      .finally(() => setLoading(false));
  }, [status, offset]);

  useEffect(() => { load(); }, [load]);

  function switchStatus(next: string) {
    setStatus(next);
    setOffset(0);
  }

  async function handleGenerate(c: BacklogCandidate) {
    setBusyId(c.id);
    setError(null);
    try {
      const res = await generateNotes([toFollowerCandidate(c)]);
      const note = res.candidates[0]?.note ?? "";
      const updated = await updateCandidate(c.id, { note });
      setDrafts((d) => ({ ...d, [c.id]: note }));
      // Saving a note advances new→noted server-side, but we keep the card in
      // place (just reflect the new status) so you can finish working it here.
      // Tab membership reconciles next time you load the list.
      setData((prev) => prev && {
        ...prev,
        candidates: prev.candidates.map((x) =>
          x.id === c.id ? { ...x, note: updated.note ?? note, status: updated.status } : x
        ),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Note generation failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSaveNote(c: BacklogCandidate) {
    setBusyId(c.id);
    setError(null);
    try {
      const note = drafts[c.id] ?? "";
      const updated = await updateCandidate(c.id, { note });
      setData((prev) => prev && {
        ...prev,
        candidates: prev.candidates.map((x) =>
          x.id === c.id ? { ...x, note: updated.note ?? note, status: updated.status } : x
        ),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleCopyOpen(c: BacklogCandidate) {
    const note = drafts[c.id] ?? "";
    if (note) await navigator.clipboard.writeText(note);
    setCopiedId(c.id);
    window.open(c.profile_url, "_blank");
    setTimeout(() => setCopiedId(null), 3000);
  }

  async function handleSetStatus(c: BacklogCandidate, next: string) {
    setBusyId(c.id);
    setError(null);
    try {
      if (next === "requested") {
        // Track it: creates a connection_request AND (server-side) marks the
        // candidate 'requested' so it leaves the backlog.
        await trackConnectionRequests([{ ...toFollowerCandidate(c), note: drafts[c.id] ?? "" }]);
      } else {
        await updateCandidate(c.id, { status: next });
      }
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  const total = data?.total ?? 0;
  const counts = data?.counts ?? {};
  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + PAGE_SIZE, total);
  const isTerminal = status === "requested" || status === "skipped";

  return (
    <div>
      {/* Status filter */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => switchStatus(tab.value)}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
              status === tab.value
                ? "border-blue-500 bg-blue-500/10 text-blue-400"
                : "border-slate-700 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {tab.label}
            <span className="ml-1.5 text-xs text-slate-500">{counts[tab.value] ?? 0}</span>
          </button>
        ))}
      </div>

      {error && <ErrorMessage message={error} />}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500" />
        </div>
      ) : !data || data.candidates.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-slate-400 text-lg">Nothing here</p>
          <p className="text-slate-500 text-sm mt-1">
            {status === "new"
              ? "Run a scan on the New Scan tab to fill your backlog."
              : `No ${status} candidates.`}
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs text-slate-500 mb-3">
            Showing {showingFrom}–{showingTo} of {total}
          </p>

          <div className="space-y-3">
            {data.candidates.map((c) => (
              <div key={c.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-white">{c.name || "(no name)"}</span>
                      <a
                        href={c.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-400"
                        title="Open LinkedIn profile"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                      </a>
                      {(c.segments ?? []).map((s) => <SegmentBadge key={s} segment={s} />)}
                    </div>
                    {c.headline && <p className="text-xs text-slate-400 truncate">{c.headline}</p>}
                    <div className="flex gap-3 mt-0.5 text-xs text-slate-500">
                      {c.company && <span>{c.company}</span>}
                      {c.location && <span>{c.location}</span>}
                    </div>
                  </div>
                  {!isTerminal && (
                    <button
                      onClick={() => handleSetStatus(c, "skipped")}
                      disabled={busyId === c.id}
                      className="shrink-0 text-xs text-slate-500 hover:text-red-400 disabled:opacity-50"
                      title="Not interested — hide from backlog"
                    >
                      Skip
                    </button>
                  )}
                  {status === "skipped" && (
                    <button
                      onClick={() => handleSetStatus(c, "new")}
                      disabled={busyId === c.id}
                      className="shrink-0 text-xs text-slate-400 hover:text-blue-400 disabled:opacity-50"
                    >
                      Restore
                    </button>
                  )}
                </div>

                {/* Note + actions (only while actionable) */}
                {!isTerminal && (
                  <div className="mt-3">
                    {drafts[c.id] !== undefined && drafts[c.id] !== "" ? (
                      <>
                        <textarea
                          value={drafts[c.id]}
                          onChange={(e) => setDrafts((d) => ({ ...d, [c.id]: e.target.value }))}
                          maxLength={300}
                          rows={3}
                          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                        />
                        <div className="flex items-center justify-between mt-2">
                          <span className={`text-xs ${(drafts[c.id]?.length ?? 0) > 280 ? "text-amber-400" : "text-slate-600"}`}>
                            {drafts[c.id]?.length ?? 0}/300
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleSaveNote(c)}
                              disabled={busyId === c.id}
                              className="px-3 py-1.5 text-xs rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                            >
                              Save note
                            </button>
                            <button
                              onClick={() => handleGenerate(c)}
                              disabled={busyId === c.id}
                              className="px-3 py-1.5 text-xs rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50"
                            >
                              {busyId === c.id ? "Working…" : "Regenerate"}
                            </button>
                            <button
                              onClick={() => handleCopyOpen(c)}
                              className={`px-3 py-1.5 text-xs font-medium rounded-lg ${
                                copiedId === c.id ? "bg-green-600/20 text-green-400 border border-green-500/30" : "bg-slate-700 text-slate-200 hover:bg-slate-600"
                              }`}
                            >
                              {copiedId === c.id ? "Copied! Opening…" : "Copy & open"}
                            </button>
                            <button
                              onClick={() => handleSetStatus(c, "requested")}
                              disabled={busyId === c.id}
                              className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50"
                            >
                              Mark requested
                            </button>
                          </div>
                        </div>
                      </>
                    ) : (
                      <button
                        onClick={() => handleGenerate(c)}
                        disabled={busyId === c.id}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50"
                      >
                        {busyId === c.id ? "Generating…" : "Generate note"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-center gap-3 mt-5">
              <button
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-40"
              >
                ← Prev
              </button>
              <span className="text-xs text-slate-500">
                {showingFrom}–{showingTo} of {total}
              </span>
              <button
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
