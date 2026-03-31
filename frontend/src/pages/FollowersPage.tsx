import { useState, useEffect } from "react";
import { scanFollowers, generateNotes, trackConnectionRequests, listConnectionRequests, checkAcceptances, getConnectionRequestStats } from "../api/followers";
import type {
  FollowerCandidate,
  CandidateWithNote,
  ScanStats,
  ConnectionRequestRecord,
  CheckAcceptancesResponse,
  ConnectionRequestStatsResponse,
} from "../types";
import SegmentBadge from "../components/SegmentBadge";
import ErrorMessage from "../components/ErrorMessage";

type Phase = "idle" | "scanning" | "candidates" | "generating" | "reviewing" | "saving" | "saved";
type Tab = "scan" | "requests";

const SEGMENT_OPTIONS = [
  { value: "mujertech", label: "MujerTech" },
  { value: "cascadia", label: "Cascadia AI" },
  { value: "job_target", label: "Job Target" },
];

export default function FollowersPage() {
  const [activeTab, setActiveTab] = useState<Tab>("scan");

  // Scan config
  const [maxFollowers, setMaxFollowers] = useState(50);
  const [maxProfiles, setMaxProfiles] = useState(15);

  // State
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  // Scan results
  const [candidates, setCandidates] = useState<FollowerCandidate[]>([]);
  const [scanStats, setScanStats] = useState<ScanStats | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [segmentFilter, setSegmentFilter] = useState<string>("");

  // Note review
  const [candidatesWithNotes, setCandidatesWithNotes] = useState<CandidateWithNote[]>([]);

  // Manual tracking
  const [markedAsSent, setMarkedAsSent] = useState<Set<string>>(new Set());
  const [savedCount, setSavedCount] = useState(0);
  const [copiedNote, setCopiedNote] = useState<string | null>(null);

  // Past requests state
  const [requests, setRequests] = useState<ConnectionRequestRecord[]>([]);
  const [requestsTotal, setRequestsTotal] = useState(0);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [requestsError, setRequestsError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [stats, setStats] = useState<ConnectionRequestStatsResponse | null>(null);
  const [checkResult, setCheckResult] = useState<CheckAcceptancesResponse | null>(null);
  const [checking, setChecking] = useState(false);

  // ── Past Requests logic ──

  async function loadRequests() {
    setRequestsLoading(true);
    setRequestsError(null);
    try {
      const [reqData, statsData] = await Promise.all([
        listConnectionRequests(statusFilter || undefined),
        getConnectionRequestStats(),
      ]);
      setRequests(reqData.requests);
      setRequestsTotal(reqData.total);
      setStats(statsData);
    } catch (err) {
      setRequestsError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setRequestsLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "requests") {
      loadRequests();
    }
  }, [activeTab, statusFilter]);

  async function handleCheckAcceptances() {
    setChecking(true);
    setCheckResult(null);
    try {
      const result = await checkAcceptances();
      setCheckResult(result);
      await loadRequests();
    } catch (err) {
      setRequestsError(err instanceof Error ? err.message : "Check failed");
    } finally {
      setChecking(false);
    }
  }

  // ── Scan logic ──

  async function handleScan() {
    setPhase("scanning");
    setError(null);
    setCandidates([]);
    setScanStats(null);

    try {
      const data = await scanFollowers(maxFollowers, maxProfiles);
      setCandidates(data.candidates);
      setScanStats(data.stats);
      setSelected(new Set(data.candidates.map((c) => c.profile_url)));
      setPhase("candidates");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
      setPhase("idle");
    }
  }

  async function handleGenerateNotes() {
    const approved = candidates.filter((c) => selected.has(c.profile_url));
    if (approved.length === 0) return;

    setPhase("generating");
    setError(null);

    try {
      const data = await generateNotes(approved);
      setCandidatesWithNotes(data.candidates);
      setPhase("reviewing");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Note generation failed");
      setPhase("candidates");
    }
  }

  function updateNote(profileUrl: string, newNote: string) {
    setCandidatesWithNotes((prev) =>
      prev.map((c) => (c.profile_url === profileUrl ? { ...c, note: newNote } : c))
    );
  }

  function removeFromReview(profileUrl: string) {
    setCandidatesWithNotes((prev) => prev.filter((c) => c.profile_url !== profileUrl));
    setMarkedAsSent((prev) => {
      const next = new Set(prev);
      next.delete(profileUrl);
      return next;
    });
  }

  // ── Segment tagging ──

  function addSegment(profileUrl: string, segment: string) {
    setCandidates((prev) =>
      prev.map((c) =>
        c.profile_url === profileUrl && !c.segments.includes(segment)
          ? { ...c, segments: [...c.segments, segment] }
          : c
      )
    );
  }

  function removeSegment(profileUrl: string, segment: string) {
    setCandidates((prev) =>
      prev.map((c) =>
        c.profile_url === profileUrl
          ? { ...c, segments: c.segments.filter((s) => s !== segment) }
          : c
      )
    );
  }

  // ── Mark as sent ──

  async function handleCopyAndOpen(candidate: CandidateWithNote) {
    await navigator.clipboard.writeText(candidate.note);
    setCopiedNote(candidate.profile_url);
    window.open(candidate.profile_url, "_blank");
    // Auto-mark as sent
    setMarkedAsSent((prev) => new Set(prev).add(candidate.profile_url));
    setTimeout(() => setCopiedNote(null), 3000);
  }

  function toggleMarkedAsSent(profileUrl: string) {
    setMarkedAsSent((prev) => {
      const next = new Set(prev);
      if (next.has(profileUrl)) {
        next.delete(profileUrl);
      } else {
        next.add(profileUrl);
      }
      return next;
    });
  }

  async function handleSaveTracked() {
    const toTrack = candidatesWithNotes.filter((c) => markedAsSent.has(c.profile_url));
    if (toTrack.length === 0) return;

    setPhase("saving");
    setError(null);

    try {
      const data = await trackConnectionRequests(toTrack);
      setSavedCount(data.saved);
      setPhase("saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
      setPhase("reviewing");
    }
  }

  // ── Selection ──

  const filteredCandidates = segmentFilter
    ? candidates.filter((c) =>
        segmentFilter === "none"
          ? c.segments.length === 0
          : c.segments.includes(segmentFilter)
      )
    : candidates;

  function toggleCandidate(profileUrl: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(profileUrl)) {
        next.delete(profileUrl);
      } else {
        next.add(profileUrl);
      }
      return next;
    });
  }

  function toggleAll() {
    const visibleUrls = filteredCandidates.map((c) => c.profile_url);
    const allVisible = visibleUrls.every((url) => selected.has(url));
    if (allVisible) {
      setSelected((prev) => {
        const next = new Set(prev);
        visibleUrls.forEach((url) => next.delete(url));
        return next;
      });
    } else {
      setSelected((prev) => {
        const next = new Set(prev);
        visibleUrls.forEach((url) => next.add(url));
        return next;
      });
    }
  }

  function handleReset() {
    setPhase("idle");
    setCandidates([]);
    setScanStats(null);
    setSelected(new Set());
    setSegmentFilter("");
    setCandidatesWithNotes([]);
    setMarkedAsSent(new Set());
    setSavedCount(0);
    setCopiedNote(null);
    setError(null);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Connect with Followers</h1>
      <p className="text-slate-400 text-sm mb-6">
        Scan your LinkedIn followers, generate personalized connection notes, and track who you've reached out to.
      </p>

      {/* ── Tabs ── */}
      <div className="flex gap-1 mb-6 border-b border-slate-700">
        <button
          onClick={() => setActiveTab("scan")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "scan"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-300"
          }`}
        >
          New Scan
        </button>
        <button
          onClick={() => setActiveTab("requests")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "requests"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-300"
          }`}
        >
          Past Requests
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════ */}
      {/* TAB: New Scan                                            */}
      {/* ══════════════════════════════════════════════════════════ */}
      {activeTab === "scan" && (
        <>
          {error && <ErrorMessage message={error} />}

          {/* ── Idle: Scan Configuration ── */}
          {phase === "idle" && (
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-lg">
              <h2 className="text-lg font-semibold text-white mb-4">Scan Settings</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">
                    How many followers to check
                  </label>
                  <input
                    type="number"
                    value={maxFollowers}
                    onChange={(e) => setMaxFollowers(Number(e.target.value))}
                    min={1}
                    max={200}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">We'll scroll through your followers list and pick up this many</p>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">
                    How many profiles to look up in detail
                  </label>
                  <input
                    type="number"
                    value={maxProfiles}
                    onChange={(e) => setMaxProfiles(Number(e.target.value))}
                    min={1}
                    max={50}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    We'll visit each profile to get their headline, company, and location (~1-2s each)
                  </p>
                </div>
              </div>

              <button
                onClick={handleScan}
                className="mt-6 w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-500 transition-colors"
              >
                Scan Followers
              </button>
            </div>
          )}

          {/* ── Scanning ── */}
          {phase === "scanning" && (
            <ScanProgress maxProfiles={maxProfiles} />
          )}

          {/* ── Candidates: Select who to connect with ── */}
          {phase === "candidates" && (
            <div>
              {/* Summary */}
              {scanStats && (
                <div className="mb-5 p-4 bg-slate-800 rounded-lg border border-slate-700">
                  <p className="text-sm text-slate-300">
                    Found <span className="text-white font-semibold">{candidates.length}</span> new follower{candidates.length !== 1 ? "s" : ""} to connect with.
                    {scanStats.already_in_db > 0 && (
                      <span className="text-slate-400"> ({scanStats.already_in_db} already in your network were skipped.)</span>
                    )}
                  </p>
                  {(scanStats.matched_mujertech > 0 || scanStats.matched_cascadia > 0 || scanStats.matched_job_target > 0) && (
                    <div className="flex gap-3 mt-2">
                      {scanStats.matched_mujertech > 0 && (
                        <span className="text-xs text-purple-400">{scanStats.matched_mujertech} MujerTech</span>
                      )}
                      {scanStats.matched_cascadia > 0 && (
                        <span className="text-xs text-teal-400">{scanStats.matched_cascadia} Cascadia AI</span>
                      )}
                      {scanStats.matched_job_target > 0 && (
                        <span className="text-xs text-amber-400">{scanStats.matched_job_target} Job Target</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {candidates.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-slate-400 text-lg">No new followers found</p>
                  <p className="text-slate-500 text-sm mt-1">
                    Everyone in this batch is already in your network. Try scanning more followers.
                  </p>
                  <button
                    onClick={handleReset}
                    className="mt-4 px-4 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
                  >
                    Scan Again
                  </button>
                </div>
              ) : (
                <>
                  {/* Toolbar */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <select
                        value={segmentFilter}
                        onChange={(e) => setSegmentFilter(e.target.value)}
                        className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">All ({candidates.length})</option>
                        {candidates.some((c) => c.segments.includes("mujertech")) && (
                          <option value="mujertech">MujerTech ({candidates.filter((c) => c.segments.includes("mujertech")).length})</option>
                        )}
                        {candidates.some((c) => c.segments.includes("cascadia")) && (
                          <option value="cascadia">Cascadia AI ({candidates.filter((c) => c.segments.includes("cascadia")).length})</option>
                        )}
                        {candidates.some((c) => c.segments.includes("job_target")) && (
                          <option value="job_target">Job Target ({candidates.filter((c) => c.segments.includes("job_target")).length})</option>
                        )}
                        {candidates.some((c) => c.segments.length === 0) && (
                          <option value="none">No segment ({candidates.filter((c) => c.segments.length === 0).length})</option>
                        )}
                      </select>
                      <button
                        onClick={toggleAll}
                        className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700"
                      >
                        {filteredCandidates.every((c) => selected.has(c.profile_url)) ? "Deselect All" : "Select All"}
                      </button>
                      <span className="text-sm text-slate-400">
                        {selected.size} selected
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleGenerateNotes}
                        disabled={selected.size === 0}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Generate Notes ({selected.size})
                      </button>
                      <button
                        onClick={handleReset}
                        className="px-3 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  {/* Candidate Cards */}
                  <div className="space-y-2">
                    {filteredCandidates.map((candidate) => (
                      <div
                        key={candidate.profile_url}
                        className={`bg-slate-800 rounded-lg border p-4 cursor-pointer transition-colors ${
                          selected.has(candidate.profile_url)
                            ? "border-blue-500/50 bg-blue-500/5"
                            : "border-slate-700 hover:border-slate-600"
                        }`}
                        onClick={() => toggleCandidate(candidate.profile_url)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="pt-0.5">
                            <div
                              className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                                selected.has(candidate.profile_url)
                                  ? "bg-blue-600 border-blue-600"
                                  : "border-slate-600"
                              }`}
                            >
                              {selected.has(candidate.profile_url) && (
                                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <span className="text-sm font-medium text-white">{candidate.name}</span>
                              <a
                                href={candidate.profile_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-blue-500 hover:text-blue-400"
                                title="Open LinkedIn profile"
                              >
                                <LinkedInIcon />
                              </a>
                              {candidate.segments.map((seg) => (
                                <span
                                  key={seg}
                                  className="inline-flex items-center gap-1"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <SegmentBadge segment={seg} />
                                  <button
                                    onClick={() => removeSegment(candidate.profile_url, seg)}
                                    className="text-slate-500 hover:text-red-400 transition-colors"
                                    title={`Remove ${seg}`}
                                  >
                                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                  </button>
                                </span>
                              ))}
                              {/* Add segment */}
                              <div onClick={(e) => e.stopPropagation()}>
                                <select
                                  value=""
                                  onChange={(e) => {
                                    if (e.target.value) addSegment(candidate.profile_url, e.target.value);
                                  }}
                                  className="px-1.5 py-0.5 bg-slate-700 border border-slate-600 rounded text-xs text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                                >
                                  <option value="">+ tag</option>
                                  {SEGMENT_OPTIONS
                                    .filter((opt) => !candidate.segments.includes(opt.value))
                                    .map((opt) => (
                                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))
                                  }
                                </select>
                              </div>
                            </div>
                            {candidate.headline && (
                              <p className="text-xs text-slate-400 truncate">{candidate.headline}</p>
                            )}
                            <div className="flex gap-3 mt-1 text-xs text-slate-500">
                              {candidate.company && <span>{candidate.company}</span>}
                              {candidate.location && <span>{candidate.location}</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Generating Notes ── */}
          {phase === "generating" && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-purple-500 mb-4" />
              <p className="text-slate-300 text-lg font-medium">Writing personalized notes...</p>
              <p className="text-slate-500 text-sm mt-1">
                Creating a custom connection note for each person with AI.
              </p>
            </div>
          )}

          {/* ── Reviewing: Copy, send, mark ── */}
          {phase === "reviewing" && (
            <div>
              {/* Step instructions */}
              <div className="mb-5 p-4 bg-slate-800 rounded-lg border border-slate-700">
                <p className="text-sm text-white font-medium mb-2">For each person:</p>
                <div className="flex gap-6 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">1</span>
                    Click "Copy & Open Profile"
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">2</span>
                    Paste the note on LinkedIn and send
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">3</span>
                    It auto-marks as sent
                  </div>
                </div>
              </div>

              {/* Toolbar */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-slate-400">
                  <span className="text-green-400 font-medium">{markedAsSent.size}</span> of {candidatesWithNotes.length} sent
                </span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleSaveTracked}
                    disabled={markedAsSent.size === 0}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Save & Track ({markedAsSent.size})
                  </button>
                  <button
                    onClick={() => setPhase("candidates")}
                    className="px-3 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
                  >
                    Back
                  </button>
                </div>
              </div>

              {/* Cards */}
              <div className="space-y-3">
                {candidatesWithNotes.map((candidate) => {
                  const isSent = markedAsSent.has(candidate.profile_url);
                  const isCopied = copiedNote === candidate.profile_url;

                  return (
                    <div
                      key={candidate.profile_url}
                      className={`bg-slate-800 rounded-lg border p-4 transition-colors ${
                        isSent
                          ? "border-green-500/40 bg-green-500/5"
                          : "border-slate-700"
                      }`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">{candidate.name}</span>
                          {candidate.segments.map((seg) => (
                            <SegmentBadge key={seg} segment={seg} />
                          ))}
                          {isSent && (
                            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-green-500/20 text-green-400">
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                              Sent
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => removeFromReview(candidate.profile_url)}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                          title="Remove"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>

                      {candidate.headline && (
                        <p className="text-xs text-slate-500 mb-3">{candidate.headline}</p>
                      )}

                      {/* Note */}
                      <textarea
                        value={candidate.note}
                        onChange={(e) => updateNote(candidate.profile_url, e.target.value)}
                        maxLength={300}
                        rows={3}
                        className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      />

                      {/* Actions row */}
                      <div className="flex items-center justify-between mt-2">
                        <span className={`text-xs ${candidate.note.length > 280 ? "text-amber-400" : "text-slate-600"}`}>
                          {candidate.note.length}/300
                        </span>

                        <div className="flex items-center gap-2">
                          {/* Toggle sent manually */}
                          <button
                            onClick={() => toggleMarkedAsSent(candidate.profile_url)}
                            className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                              isSent
                                ? "border-green-500/40 text-green-400 hover:bg-green-500/10"
                                : "border-slate-600 text-slate-400 hover:bg-slate-700"
                            }`}
                          >
                            {isSent ? "Undo sent" : "Mark as sent"}
                          </button>

                          {/* Main action: Copy & Open */}
                          <button
                            onClick={() => handleCopyAndOpen(candidate)}
                            className={`px-4 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                              isCopied
                                ? "bg-green-600/20 text-green-400 border border-green-500/30"
                                : "bg-blue-600 text-white hover:bg-blue-500"
                            }`}
                          >
                            {isCopied ? "Copied! Opening profile..." : "Copy & Open Profile"}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Saving ── */}
          {phase === "saving" && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-green-500 mb-4" />
              <p className="text-slate-300 text-lg font-medium">Saving tracked requests...</p>
            </div>
          )}

          {/* ── Saved ── */}
          {phase === "saved" && (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/20 mb-4">
                <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-white text-lg font-medium">
                {savedCount} connection{savedCount !== 1 ? "s" : ""} tracked!
              </p>
              <p className="text-slate-400 text-sm mt-2">
                Check the Past Requests tab to monitor acceptances.
              </p>
              <div className="flex justify-center gap-3 mt-6">
                <button
                  onClick={() => setActiveTab("requests")}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition-colors"
                >
                  View Past Requests
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
                >
                  Start New Scan
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* TAB: Past Requests                                       */}
      {/* ══════════════════════════════════════════════════════════ */}
      {activeTab === "requests" && (
        <div>
          {requestsError && <ErrorMessage message={requestsError} />}

          {/* Stats */}
          {stats && stats.total_requests > 0 && (
            <div className="flex flex-wrap gap-3 mb-6">
              <StatCard label="Total Sent" value={stats.total_requests} />
              <StatCard label="Accepted" value={stats.total_accepted} color="green" />
              <StatCard label="Pending" value={stats.total_pending} color="yellow" />
              <StatCard label="Failed" value={stats.total_failed} color="red" />
              <div className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center min-w-20">
                <p className="text-lg font-bold text-blue-400">{stats.overall_acceptance_rate}%</p>
                <p className="text-xs text-slate-500">Accept Rate</p>
              </div>
            </div>
          )}

          {/* Segment Breakdown */}
          {stats && stats.by_segment.length > 0 && (
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
              <h3 className="text-sm font-semibold text-white mb-3">Acceptance by Segment</h3>
              <div className="space-y-2">
                {stats.by_segment.map((seg) => (
                  <div key={seg.segment} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <SegmentBadge segment={seg.segment} />
                      <span className="text-xs text-slate-400">
                        {seg.accepted}/{seg.total_sent} accepted
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full transition-all"
                          style={{ width: `${seg.acceptance_rate}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-slate-300 w-12 text-right">
                        {seg.acceptance_rate}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="failed">Failed</option>
              </select>
              <span className="text-sm text-slate-400">
                {requestsTotal} request{requestsTotal !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleCheckAcceptances}
                disabled={checking}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {checking ? "Checking..." : "Check Acceptances"}
              </button>
              <button
                onClick={loadRequests}
                disabled={requestsLoading}
                className="px-3 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Check Result Banner */}
          {checkResult && (
            <div className={`mb-4 p-4 rounded-lg border ${
              checkResult.newly_accepted > 0
                ? "bg-green-500/10 border-green-500/30"
                : "bg-slate-800 border-slate-700"
            }`}>
              <p className={`text-sm font-medium ${
                checkResult.newly_accepted > 0 ? "text-green-300" : "text-slate-300"
              }`}>
                {checkResult.newly_accepted > 0
                  ? `${checkResult.newly_accepted} new acceptance${checkResult.newly_accepted > 1 ? "s" : ""} found!`
                  : "No new acceptances found."
                }
              </p>
              {checkResult.accepted_names.length > 0 && (
                <p className="text-xs text-green-400/70 mt-1">
                  {checkResult.accepted_names.join(", ")}
                </p>
              )}
              <p className="text-xs text-slate-500 mt-1">
                Checked {checkResult.checked} pending request{checkResult.checked !== 1 ? "s" : ""}.
                {checkResult.still_pending > 0 && ` ${checkResult.still_pending} still pending.`}
              </p>
            </div>
          )}

          {/* Loading */}
          {requestsLoading && (
            <div className="flex justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500" />
            </div>
          )}

          {/* Empty State */}
          {!requestsLoading && requests.length === 0 && (
            <div className="text-center py-12">
              <p className="text-slate-400 text-lg">No connection requests yet</p>
              <p className="text-slate-500 text-sm mt-1">
                Requests will appear here after you scan and track connections.
              </p>
            </div>
          )}

          {/* Requests List */}
          {!requestsLoading && requests.length > 0 && (
            <div className="space-y-2">
              {requests.map((req) => (
                <div
                  key={req.id}
                  className={`bg-slate-800 rounded-lg border p-4 ${
                    req.status === "accepted"
                      ? "border-green-500/30"
                      : req.status === "pending"
                      ? "border-yellow-500/20"
                      : "border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white">{req.name}</span>
                        <a
                          href={req.profile_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:text-blue-400"
                        >
                          <LinkedInIcon />
                        </a>
                        {req.segments && req.segments.map((seg) => (
                          <SegmentBadge key={seg} segment={seg} />
                        ))}
                      </div>
                      {req.headline && (
                        <p className="text-xs text-slate-400 truncate">{req.headline}</p>
                      )}
                      <div className="flex gap-3 mt-1 text-xs text-slate-500">
                        {req.company && <span>{req.company}</span>}
                        {req.location && <span>{req.location}</span>}
                      </div>
                      {req.note_sent && (
                        <p className="text-xs text-slate-500 mt-2 bg-slate-700/50 rounded p-2 whitespace-pre-wrap">
                          {req.note_sent}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 ml-4">
                      <RequestStatusBadge status={req.status} />
                      <span className="text-xs text-slate-600">
                        {new Date(req.sent_at).toLocaleDateString()}
                      </span>
                      {req.accepted_at && (
                        <span className="text-xs text-green-600">
                          Accepted {new Date(req.accepted_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helper Components ──

function LinkedInIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
    </svg>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  const colorMap: Record<string, string> = {
    purple: "text-purple-400",
    teal: "text-teal-400",
    amber: "text-amber-400",
    green: "text-green-400",
    blue: "text-blue-400",
    yellow: "text-yellow-400",
    red: "text-red-400",
  };
  const textColor = color ? colorMap[color] ?? "text-white" : "text-white";

  return (
    <div className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-center min-w-20">
      <p className={`text-lg font-bold ${textColor}`}>{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

function RequestStatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    sent: { bg: "bg-green-500/20", text: "text-green-400", label: "Sent" },
    pending: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Pending" },
    accepted: { bg: "bg-green-500/20", text: "text-green-400", label: "Accepted" },
    rejected: { bg: "bg-red-500/20", text: "text-red-400", label: "Rejected" },
    withdrawn: { bg: "bg-slate-500/20", text: "text-slate-400", label: "Withdrawn" },
    already_connected: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Already Connected" },
    already_pending: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Already Pending" },
    failed: { bg: "bg-red-500/20", text: "text-red-400", label: "Failed" },
  };
  const style = styles[status] ?? { bg: "bg-slate-700", text: "text-slate-400", label: status };

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

const SCAN_STEPS = [
  { label: "Opening LinkedIn...", duration: 3000 },
  { label: "Verifying you're logged in...", duration: 2000 },
  { label: "Reading your followers list...", duration: 5000 },
  { label: "Looking up profile details...", duration: 2000 },
];

function ScanProgress({ maxProfiles }: { maxProfiles: number }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [profileCount, setProfileCount] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (currentStep >= SCAN_STEPS.length) return;
    const timer = setTimeout(() => {
      setCurrentStep((s) => s + 1);
    }, SCAN_STEPS[currentStep].duration);
    return () => clearTimeout(timer);
  }, [currentStep]);

  useEffect(() => {
    if (currentStep < SCAN_STEPS.length) return;
    if (profileCount >= maxProfiles) return;
    const interval = setInterval(() => {
      setProfileCount((c) => Math.min(c + 1, maxProfiles));
    }, 1500);
    return () => clearInterval(interval);
  }, [currentStep, profileCount, maxProfiles]);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const enriching = currentStep >= SCAN_STEPS.length;

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500 mb-6" />

      <p className="text-slate-200 text-lg font-medium mb-1">
        {enriching
          ? `Looking up profile ${profileCount} of ${maxProfiles}...`
          : SCAN_STEPS[currentStep].label}
      </p>

      <div className="mt-4 space-y-2 text-sm">
        {SCAN_STEPS.map((step, i) => (
          <div key={i} className="flex items-center gap-2">
            {i < currentStep ? (
              <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            ) : i === currentStep ? (
              <div className="w-4 h-4 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" />
            ) : (
              <div className="w-4 h-4 rounded-full border-2 border-slate-600" />
            )}
            <span className={i <= currentStep ? "text-slate-300" : "text-slate-600"}>
              {step.label}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-2">
          {enriching ? (
            <div className="w-4 h-4 animate-spin rounded-full border-2 border-slate-600 border-t-blue-400" />
          ) : (
            <div className="w-4 h-4 rounded-full border-2 border-slate-600" />
          )}
          <span className={enriching ? "text-slate-300" : "text-slate-600"}>
            {enriching
              ? `Getting profile details (${profileCount}/${maxProfiles})...`
              : `Look up ${maxProfiles} profiles`}
          </span>
        </div>
      </div>

      <p className="text-slate-600 text-xs mt-6">
        {elapsedSeconds}s elapsed
        {enriching && profileCount < maxProfiles && " — about 1-2s per profile"}
      </p>
    </div>
  );
}
