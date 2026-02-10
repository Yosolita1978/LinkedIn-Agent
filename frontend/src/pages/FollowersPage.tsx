import { useState, useEffect } from "react";
import { scanFollowers, generateNotes, connectWithCandidates } from "../api/followers";
import type { FollowerCandidate, CandidateWithNote, ScanStats, ConnectResult, ConnectStats } from "../types";
import SegmentBadge from "../components/SegmentBadge";
import ErrorMessage from "../components/ErrorMessage";

type Phase = "idle" | "scanning" | "candidates" | "generating" | "reviewing" | "connecting" | "results";

export default function FollowersPage() {
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

  // Note review
  const [candidatesWithNotes, setCandidatesWithNotes] = useState<CandidateWithNote[]>([]);

  // Connect results
  const [connectResults, setConnectResults] = useState<ConnectResult[]>([]);
  const [connectStats, setConnectStats] = useState<ConnectStats | null>(null);
  const [maxConnections, setMaxConnections] = useState(10);

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
  }

  async function handleConnect() {
    if (candidatesWithNotes.length === 0) return;

    setPhase("connecting");
    setError(null);

    try {
      const data = await connectWithCandidates(candidatesWithNotes, maxConnections);
      setConnectResults(data.results);
      setConnectStats(data.stats);
      setPhase("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed");
      setPhase("reviewing");
    }
  }

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
    if (selected.size === candidates.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(candidates.map((c) => c.profile_url)));
    }
  }

  function handleReset() {
    setPhase("idle");
    setCandidates([]);
    setScanStats(null);
    setSelected(new Set());
    setCandidatesWithNotes([]);
    setConnectResults([]);
    setConnectStats(null);
    setError(null);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-2">Connect with Followers</h1>
      <p className="text-slate-400 text-sm mb-6">
        Scan your LinkedIn followers, filter by segment, and send personalized connection requests.
      </p>

      {error && <ErrorMessage message={error} />}

      {/* ── Idle: Scan Configuration ── */}
      {phase === "idle" && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 max-w-lg">
          <h2 className="text-lg font-semibold text-white mb-4">Scan Settings</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">
                Max followers to scrape
              </label>
              <input
                type="number"
                value={maxFollowers}
                onChange={(e) => setMaxFollowers(Number(e.target.value))}
                min={1}
                max={200}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">How many followers to read from the list</p>
            </div>

            <div>
              <label className="block text-sm text-slate-400 mb-1">
                Max profiles to enrich
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
                Each profile takes ~1-2 seconds via API.
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

      {/* ── Scanning: Loading State with Progress ── */}
      {phase === "scanning" && (
        <ScanProgress maxProfiles={maxProfiles} />
      )}

      {/* ── Candidates: Select who to connect with ── */}
      {phase === "candidates" && (
        <div>
          {scanStats && (
            <div className="flex flex-wrap gap-3 mb-6">
              <StatCard label="Followers scraped" value={scanStats.followers_scraped} />
              <StatCard label="Already known" value={scanStats.already_in_db} />
              <StatCard label="Profiles enriched" value={scanStats.profiles_enriched} />
              <StatCard label="MujerTech" value={scanStats.matched_mujertech} color="purple" />
              <StatCard label="Cascadia AI" value={scanStats.matched_cascadia} color="teal" />
              <StatCard label="Job Target" value={scanStats.matched_job_target} color="amber" />
              <StatCard label="No match" value={scanStats.no_segment} />
            </div>
          )}

          {candidates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-400 text-lg">No matching followers found</p>
              <p className="text-slate-500 text-sm mt-1">
                Try scanning more followers or adjusting your settings.
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
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={toggleAll}
                    className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700"
                  >
                    {selected.size === candidates.length ? "Deselect All" : "Select All"}
                  </button>
                  <span className="text-sm text-slate-400">
                    {selected.size} of {candidates.length} selected
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

              <div className="space-y-2">
                {candidates.map((candidate) => (
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
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium text-white">{candidate.name}</span>
                          <a
                            href={candidate.profile_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-500 hover:text-blue-400"
                            title="Open LinkedIn profile"
                          >
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                            </svg>
                          </a>
                          {candidate.segments.map((seg) => (
                            <SegmentBadge key={seg} segment={seg} />
                          ))}
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

      {/* ── Generating Notes: Loading ── */}
      {phase === "generating" && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-purple-500 mb-4" />
          <p className="text-slate-300 text-lg font-medium">Generating personalized notes...</p>
          <p className="text-slate-500 text-sm mt-1">
            Writing a custom connection note for each person with AI.
          </p>
        </div>
      )}

      {/* ── Reviewing: Edit notes before sending ── */}
      {phase === "reviewing" && (
        <div>
          <div className="mb-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-blue-300 text-sm font-medium">Review your connection notes</p>
            <p className="text-blue-400/70 text-xs mt-1">
              Edit any note before sending. Remove candidates you don't want to connect with.
            </p>
          </div>

          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-slate-400">
              {candidatesWithNotes.length} candidates ready
            </span>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-400">Max:</label>
                <input
                  type="number"
                  value={maxConnections}
                  onChange={(e) => setMaxConnections(Number(e.target.value))}
                  min={1}
                  max={25}
                  className="w-16 px-2 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleConnect}
                disabled={candidatesWithNotes.length === 0}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Send Connections ({candidatesWithNotes.length})
              </button>
              <button
                onClick={() => setPhase("candidates")}
                className="px-3 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
              >
                Back
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {candidatesWithNotes.map((candidate) => (
              <div
                key={candidate.profile_url}
                className="bg-slate-800 rounded-lg border border-slate-700 p-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{candidate.name}</span>
                    <a
                      href={candidate.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-400"
                    >
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                      </svg>
                    </a>
                    {candidate.segments.map((seg) => (
                      <SegmentBadge key={seg} segment={seg} />
                    ))}
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
                  <p className="text-xs text-slate-500 mb-2">{candidate.headline}</p>
                )}

                <textarea
                  value={candidate.note}
                  onChange={(e) => updateNote(candidate.profile_url, e.target.value)}
                  maxLength={300}
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
                <div className="flex justify-between mt-1">
                  <span className={`text-xs ${candidate.note.length > 280 ? "text-amber-400" : "text-slate-600"}`}>
                    {candidate.note.length}/300
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Connecting: Loading State ── */}
      {phase === "connecting" && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-green-500 mb-4" />
          <p className="text-slate-300 text-lg font-medium">Sending connection requests...</p>
          <p className="text-slate-500 text-sm mt-1">
            Opening each profile and sending your notes. 15-30 seconds between each.
          </p>
        </div>
      )}

      {/* ── Results: Connection Outcomes ── */}
      {phase === "results" && (
        <div>
          {connectStats && (
            <div className="flex flex-wrap gap-3 mb-6">
              <StatCard label="Total" value={connectStats.total} />
              <StatCard label="Sent" value={connectStats.sent} color="green" />
              <StatCard label="Already connected" value={connectStats.already_connected} color="blue" />
              <StatCard label="Already pending" value={connectStats.already_pending} color="yellow" />
              <StatCard label="Manual needed" value={connectStats.note_not_supported} color="amber" />
              <StatCard label="Failed" value={connectStats.failed} color="red" />
            </div>
          )}

          <div className="space-y-2">
            {connectResults.map((result, i) => (
              <div
                key={i}
                className={`bg-slate-800 rounded-lg border p-4 ${
                  result.status === "note_not_supported"
                    ? "border-amber-500/30"
                    : result.success
                    ? "border-green-500/30"
                    : result.status === "already_connected" || result.status === "already_pending"
                    ? "border-slate-700"
                    : "border-red-500/30"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-white">{result.name}</span>
                      {result.segments.map((seg) => (
                        <SegmentBadge key={seg} segment={seg} />
                      ))}
                    </div>
                    <a
                      href={result.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:text-blue-400"
                    >
                      {result.profile_url}
                    </a>
                  </div>
                  <ResultBadge status={result.status} />
                </div>

                {result.note_sent && (
                  <p className="text-sm text-slate-300 mt-2 bg-slate-700/50 rounded p-3 whitespace-pre-wrap">
                    {result.note_sent}
                  </p>
                )}

                {/* Manual note action needed */}
                {result.status === "note_not_supported" && result.note_for_manual && (
                  <div className="mt-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded">
                    <p className="text-xs text-amber-300 font-medium mb-1">
                      Connection sent without note. Copy the note below and send it manually as a message:
                    </p>
                    <p className="text-sm text-slate-300 bg-slate-700/50 rounded p-2 whitespace-pre-wrap">
                      {result.note_for_manual}
                    </p>
                    <button
                      onClick={() => navigator.clipboard.writeText(result.note_for_manual)}
                      className="mt-2 px-3 py-1 text-xs bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
                    >
                      Copy to clipboard
                    </button>
                  </div>
                )}

                {result.error && result.status !== "note_not_supported" && (
                  <p className="text-xs text-red-400 mt-2">{result.error}</p>
                )}
              </div>
            ))}
          </div>

          <button
            onClick={handleReset}
            className="mt-6 px-4 py-2 border border-slate-600 text-slate-300 rounded-lg text-sm hover:bg-slate-700"
          >
            Start New Scan
          </button>
        </div>
      )}
    </div>
  );
}

// ── Helper Components ──

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
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

function ResultBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    sent: { bg: "bg-green-500/20", text: "text-green-400", label: "Sent" },
    already_connected: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Already Connected" },
    already_pending: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Already Pending" },
    note_not_supported: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Manual Note Needed" },
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
  { label: "Starting browser...", duration: 3000 },
  { label: "Checking LinkedIn authentication...", duration: 2000 },
  { label: "Scrolling through followers list...", duration: 5000 },
  { label: "Enriching profiles via API...", duration: 2000 },
];

function ScanProgress({
  maxProfiles,
}: {
  maxProfiles: number;
}) {
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
          ? `Enriching profile ${profileCount} of ${maxProfiles}...`
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
              ? `Enriching profiles (${profileCount}/${maxProfiles})...`
              : `Enrich ${maxProfiles} profiles`}
          </span>
        </div>
      </div>

      <p className="text-slate-600 text-xs mt-6">
        {elapsedSeconds}s elapsed
        {enriching && profileCount < maxProfiles && " — about 1-2s per profile via API"}
      </p>
    </div>
  );
}
