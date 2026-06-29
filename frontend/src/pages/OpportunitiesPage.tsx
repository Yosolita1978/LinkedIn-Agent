import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOpportunities, dismissOpportunity } from "../api/resurrection";
import { generateMessage, fetchPurposes } from "../api/generate";
import { addToQueue } from "../api/queue";
import { fetchContacts } from "../api/contacts";
import type { ResurrectionOpportunity, Purpose, GenerateResponse, Contact } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import SegmentBadge from "../components/SegmentBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";
import Funnel, { type FunnelStage } from "../components/Funnel";

const HOOK_TABS = [
  { value: "", label: "All" },
  { value: "dormant", label: "Dormant" },
  { value: "promise_made", label: "Promise Made" },
  { value: "question_unanswered", label: "Unanswered" },
  { value: "they_waiting", label: "They Waiting" },
];

// How long since the last real LinkedIn message, in human terms.
function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "no messages";
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  if (days < 1) return "today";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

export default function OpportunitiesPage() {
  const [mode, setMode] = useState<"reconnect" | "opportunities">("reconnect");

  // Reconnect list (real contacts, oldest conversation first)
  const [contacts, setContacts] = useState<Contact[]>([]);

  // Opportunities (hook-based)
  const [opportunities, setOpportunities] = useState<ResurrectionOpportunity[]>([]);
  const [oppCount, setOppCount] = useState(0);
  const [activeTab, setActiveTab] = useState("");

  const [purposes, setPurposes] = useState<Purpose[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Shared generate/queue state (one row open at a time, keyed by row id)
  const [activeGenId, setActiveGenId] = useState<string | null>(null);
  const [genPurpose, setGenPurpose] = useState("reconnect");
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [selectedVariation, setSelectedVariation] = useState<number | null>(null);
  const [queueSuccess, setQueueSuccess] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  // Load everything once: purposes + funnel count + both lists.
  function loadAll() {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchPurposes(),
      fetchOpportunities(),
      fetchContacts({ sort_by: "last_message", sort_order: "asc", page_size: 30 }),
    ])
      .then(([purposeData, oppData, contactData]) => {
        setPurposes(purposeData.purposes);
        setOpportunities(oppData.opportunities);
        setOppCount(oppData.count);
        // Only people you've actually messaged before can be "reconnected" with.
        setContacts(contactData.contacts.filter((c) => c.last_message_date));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadAll(); }, []);

  // Re-fetch opportunities when the hook filter changes (opportunities mode only).
  useEffect(() => {
    if (mode !== "opportunities") return;
    fetchOpportunities(activeTab || undefined)
      .then((d) => { setOpportunities(d.opportunities); setOppCount(d.count); })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [activeTab, mode]);

  async function handleDismiss(oppId: string) {
    try {
      await dismissOpportunity(oppId);
      setOpportunities((prev) => prev.filter((o) => o.id !== oppId));
      setOppCount((c) => Math.max(0, c - 1));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dismiss failed");
    }
  }

  function openGenerate(rowId: string, defaultPurpose: string) {
    setActiveGenId(rowId);
    setGenPurpose(defaultPurpose);
    setGenResult(null);
    setGenError(null);
    setSelectedVariation(null);
    setQueueSuccess(false);
    setQueueError(null);
  }

  // Switch lists and close any open generate panel, so an unsaved draft from one
  // mode never lingers (hidden) when you move to the other.
  function switchMode(next: "reconnect" | "opportunities") {
    setMode(next);
    setActiveGenId(null);
    setGenResult(null);
    setGenError(null);
    setSelectedVariation(null);
    setQueueSuccess(false);
    setQueueError(null);
  }

  async function handleGenerate(contactId: string) {
    setGenerating(true);
    setGenError(null);
    setGenResult(null);
    setSelectedVariation(null);
    setQueueSuccess(false);
    try {
      const result = await generateMessage({
        contact_id: contactId,
        purpose: genPurpose,
        num_variations: 2,
      });
      setGenResult(result);
      if (result.variations.length > 0) setSelectedVariation(0);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleAddToQueue(contactId: string, useCase: string) {
    if (selectedVariation === null || !genResult) return;
    setQueueError(null);
    try {
      await addToQueue({
        contact_id: contactId,
        use_case: useCase,
        outreach_type: "resurrection",
        purpose: genPurpose,
        generated_message: genResult.variations[selectedVariation],
      });
      setQueueSuccess(true);
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : "Queue failed");
    }
  }

  const reactivateStages: FunnelStage[] = [
    { label: "Opportunity", count: oppCount },
    { label: "Drafted", count: null },
    { label: "Sent", count: null },
    { label: "Responded", count: null, emphasis: true },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Reactivate</h1>
      <p className="text-slate-400 text-sm mb-6">
        Restart dormant conversations — your second funnel.
      </p>

      <div className="mb-6">
        <Funnel stages={reactivateStages} />
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 mb-4 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
        <button
          onClick={() => switchMode("reconnect")}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            mode === "reconnect" ? "bg-slate-700 text-white shadow-sm" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Reconnect (oldest first)
        </button>
        <button
          onClick={() => switchMode("opportunities")}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            mode === "opportunities" ? "bg-slate-700 text-white shadow-sm" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          Opportunities
        </button>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadAll} />}
      {loading && <LoadingSpinner />}

      {/* ── Reconnect mode: real contacts, oldest conversation first ── */}
      {!loading && !error && mode === "reconnect" && (
        contacts.length === 0 ? (
          <EmptyState
            title="No past conversations found"
            description="Import your LinkedIn messages (or sync the Inbox) so the tool knows who you last talked to and when."
          />
        ) : (
          <>
            <p className="text-xs text-slate-500 mb-3">
              {contacts.length} contacts · longest since last message first
            </p>
            <div className="space-y-3">
              {contacts.map((c) => (
                <div key={c.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link to={`/contacts/${c.id}`} className="text-sm font-medium text-blue-400 hover:text-blue-300">
                          {c.name}
                        </Link>
                        {c.linkedin_url && (
                          <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-400" title="Open LinkedIn profile">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                          </a>
                        )}
                        {(c.segment_tags ?? []).map((s) => <SegmentBadge key={s} segment={s} />)}
                      </div>
                      <p className="text-xs text-slate-500">{c.company ?? c.headline ?? ""}</p>
                      <p className="text-xs text-amber-400/90 mt-1">
                        Last message: {timeAgo(c.last_message_date)}
                        {c.last_message_date && (
                          <span className="text-slate-600"> ({new Date(c.last_message_date).toLocaleDateString()})</span>
                        )}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <WarmthBadge score={c.warmth_score} size="sm" />
                      <button
                        onClick={() => openGenerate(c.id, "reconnect")}
                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500 whitespace-nowrap"
                      >
                        Generate reconnect
                      </button>
                    </div>
                  </div>

                  {activeGenId === c.id && (
                    <GeneratePanel
                      contactId={c.id}
                      useCase={c.segment_tags?.[0] ?? "general"}
                      purposes={purposes}
                      genPurpose={genPurpose}
                      setGenPurpose={setGenPurpose}
                      generating={generating}
                      onGenerate={handleGenerate}
                      genError={genError}
                      genResult={genResult}
                      selectedVariation={selectedVariation}
                      setSelectedVariation={setSelectedVariation}
                      queueSuccess={queueSuccess}
                      queueError={queueError}
                      onAddToQueue={handleAddToQueue}
                    />
                  )}
                </div>
              ))}
            </div>
          </>
        )
      )}

      {/* ── Opportunities mode: hook-based resurrection ── */}
      {!loading && !error && mode === "opportunities" && (
        <>
          <div className="flex gap-1 mb-4 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
            {HOOK_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab.value ? "bg-slate-700 text-white shadow-sm" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {opportunities.length === 0 ? (
            <EmptyState title="No opportunities found" description="Run a resurrection scan from the backend to detect opportunities" />
          ) : (
            <>
              <p className="text-xs text-slate-500 mb-3">{oppCount} opportunity(ies)</p>
              <div className="space-y-3">
                {opportunities.map((opp) => (
                  <div key={opp.id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Link to={`/contacts/${opp.contact_id}`} className="text-sm font-medium text-blue-400 hover:text-blue-300">
                            {opp.contact_name}
                          </Link>
                          {opp.contact_linkedin_url && (
                            <a href={opp.contact_linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-400" title="Open LinkedIn profile">
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                            </a>
                          )}
                        </div>
                        <p className="text-xs text-slate-500">{opp.contact_company ?? opp.contact_headline ?? ""}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs bg-amber-500/20 text-amber-400 rounded-full px-2 py-0.5 font-medium capitalize">
                          {opp.hook_type.replace("_", " ")}
                        </span>
                        <WarmthBadge score={opp.warmth_score} size="sm" />
                      </div>
                    </div>

                    {opp.hook_detail && (
                      <p className="text-sm text-slate-300 mt-2 bg-slate-700/50 rounded p-2">{opp.hook_detail}</p>
                    )}

                    <div className="flex gap-2 mt-3">
                      <Link to={`/contacts/${opp.contact_id}`} className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700">
                        View Contact
                      </Link>
                      <button onClick={() => openGenerate(opp.id, "reconnect")} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500">
                        Generate &amp; Queue
                      </button>
                      <button onClick={() => handleDismiss(opp.id)} className="px-3 py-1.5 text-sm text-slate-500 border border-slate-600 rounded-lg hover:bg-slate-700">
                        Dismiss
                      </button>
                    </div>

                    {activeGenId === opp.id && (
                      <GeneratePanel
                        contactId={opp.contact_id}
                        useCase="cascadia"
                        purposes={purposes}
                        genPurpose={genPurpose}
                        setGenPurpose={setGenPurpose}
                        generating={generating}
                        onGenerate={handleGenerate}
                        genError={genError}
                        genResult={genResult}
                        selectedVariation={selectedVariation}
                        setSelectedVariation={setSelectedVariation}
                        queueSuccess={queueSuccess}
                        queueError={queueError}
                        onAddToQueue={handleAddToQueue}
                      />
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

// Shared inline generate→queue panel, used by both the reconnect list and the
// opportunities list.
function GeneratePanel(props: {
  contactId: string;
  useCase: string;
  purposes: Purpose[];
  genPurpose: string;
  setGenPurpose: (v: string) => void;
  generating: boolean;
  onGenerate: (contactId: string) => void;
  genError: string | null;
  genResult: GenerateResponse | null;
  selectedVariation: number | null;
  setSelectedVariation: (i: number) => void;
  queueSuccess: boolean;
  queueError: string | null;
  onAddToQueue: (contactId: string, useCase: string) => void;
}) {
  const {
    contactId, useCase, purposes, genPurpose, setGenPurpose, generating, onGenerate,
    genError, genResult, selectedVariation, setSelectedVariation, queueSuccess, queueError, onAddToQueue,
  } = props;

  return (
    <div className="mt-4 pt-4 border-t border-slate-700">
      <div className="flex gap-3 mb-3">
        <select
          value={genPurpose}
          onChange={(e) => setGenPurpose(e.target.value)}
          className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200"
        >
          {purposes.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
        </select>
        <button
          onClick={() => onGenerate(contactId)}
          disabled={generating}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate"}
        </button>
      </div>

      {genError && <ErrorMessage message={genError} />}

      {genResult && (
        <div className="space-y-2">
          {genResult.variations.map((variation, i) => (
            <button
              key={i}
              onClick={() => setSelectedVariation(i)}
              className={`w-full text-left p-3 rounded-lg border text-sm ${
                selectedVariation === i ? "border-blue-500 bg-blue-500/10" : "border-slate-600 hover:bg-slate-700"
              }`}
            >
              <p className="text-slate-200 whitespace-pre-wrap">{variation}</p>
            </button>
          ))}

          {selectedVariation !== null && !queueSuccess && (
            <button
              onClick={() => onAddToQueue(contactId, useCase)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500"
            >
              Add to Queue
            </button>
          )}
          {queueError && <p className="text-sm text-red-400">{queueError}</p>}
          {queueSuccess && (
            <p className="text-sm text-green-400">
              Added to queue! <Link to="/queue" className="underline">View in Conversations</Link>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
