import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRecommendations } from "../api/ranking";
import { generateMessage, fetchPurposes } from "../api/generate";
import { addToQueue } from "../api/queue";
import type { Recommendation, Purpose, GenerateResponse } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import PriorityBadge from "../components/PriorityBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

const SEGMENT_TABS = [
  { value: "", label: "All" },
  { value: "mujertech", label: "MujerTech" },
  { value: "cascadia", label: "Cascadia" },
  { value: "job_target", label: "Job Target" },
];

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [totalEligible, setTotalEligible] = useState(0);
  const [activeTab, setActiveTab] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purposes, setPurposes] = useState<Purpose[]>([]);
  const [skippedIds, setSkippedIds] = useState<Set<string>>(new Set());

  // Generate state per recommendation
  const [activeGenId, setActiveGenId] = useState<string | null>(null);
  const [genPurpose, setGenPurpose] = useState("reconnect");
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [selectedVariation, setSelectedVariation] = useState<number | null>(null);
  const [queueSuccess, setQueueSuccess] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  function loadData() {
    setLoading(true);
    setError(null);

    Promise.all([
      fetchRecommendations(30, activeTab || undefined),
      fetchPurposes(),
    ])
      .then(([recData, purposeData]) => {
        setRecommendations(recData.recommendations);
        setTotalEligible(recData.total_eligible);
        setPurposes(purposeData.purposes);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, [activeTab]);

  function handleSkip(contactId: string) {
    setSkippedIds((prev) => new Set(prev).add(contactId));
  }

  function openGenerate(contactId: string) {
    setActiveGenId(contactId);
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

  async function handleAddToQueue(rec: Recommendation) {
    if (selectedVariation === null || !genResult) return;
    setQueueError(null);

    try {
      await addToQueue({
        contact_id: rec.contact_id,
        use_case: rec.segment_tags?.[0] ?? "general",
        outreach_type: "recommendation",
        purpose: genPurpose,
        generated_message: genResult.variations[selectedVariation],
      });
      setQueueSuccess(true);
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : "Queue failed");
    }
  }

  const visibleRecs = recommendations.filter((r) => !skippedIds.has(r.contact_id));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Today's Outreach</h1>
        <span className="text-xs text-slate-500">{totalEligible} eligible contacts</span>
      </div>

      {/* Segment Tabs */}
      <div className="flex gap-1 mb-4 bg-slate-800 rounded-lg p-1 w-fit border border-slate-700">
        {SEGMENT_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.value
                ? "bg-slate-700 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <ErrorMessage message={error} onRetry={loadData} />}
      {loading && <LoadingSpinner />}

      {!loading && !error && visibleRecs.length === 0 && (
        <EmptyState
          title="No recommendations"
          description="Run warmth scoring and resurrection scans to generate outreach recommendations"
        />
      )}

      {!loading && !error && visibleRecs.length > 0 && (
        <div className="space-y-3">
          {visibleRecs.map((rec) => (
            <div key={rec.contact_id} className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              {/* Header row */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/contacts/${rec.contact_id}`}
                      className="text-sm font-medium text-blue-400 hover:text-blue-300"
                    >
                      {rec.contact_name}
                    </Link>
                    {rec.contact_linkedin_url && (
                      <a
                        href={rec.contact_linkedin_url}
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
                  <p className="text-xs text-slate-500">{rec.contact_company ?? rec.contact_headline ?? ""}</p>
                </div>
                <div className="flex items-center gap-2">
                  <PriorityBadge score={rec.priority_score} />
                  <WarmthBadge score={rec.warmth_score} size="sm" />
                </div>
              </div>

              {/* Segment tags */}
              {rec.segment_tags && rec.segment_tags.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {rec.segment_tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-xs bg-purple-500/20 text-purple-400 rounded-full px-2 py-0.5 font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Reasons */}
              {rec.reasons.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-slate-500 mb-1">Why reach out:</p>
                  <ul className="space-y-0.5">
                    {rec.reasons.map((reason, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-1.5">
                        <span className="text-emerald-400 mt-0.5 shrink-0">-</span>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Priority breakdown bar */}
              <div className="flex items-center gap-2 mt-3">
                <div className="flex rounded-full overflow-hidden h-2 flex-1 bg-slate-700">
                  <div
                    className="bg-red-400"
                    style={{ width: `${rec.priority_breakdown.warmth_component}%` }}
                    title={`Warmth: ${rec.priority_breakdown.warmth_component}`}
                  />
                  <div
                    className="bg-purple-400"
                    style={{ width: `${rec.priority_breakdown.segment_component}%` }}
                    title={`Segment: ${rec.priority_breakdown.segment_component}`}
                  />
                  <div
                    className="bg-amber-400"
                    style={{ width: `${rec.priority_breakdown.urgency_component}%` }}
                    title={`Urgency: ${rec.priority_breakdown.urgency_component}`}
                  />
                </div>
                <span className="text-xs text-slate-600 shrink-0 w-20 text-right">
                  W:{rec.priority_breakdown.warmth_component} S:{rec.priority_breakdown.segment_component} U:{rec.priority_breakdown.urgency_component}
                </span>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-3">
                <Link
                  to={`/contacts/${rec.contact_id}`}
                  className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700"
                >
                  View Contact
                </Link>
                <button
                  onClick={() => openGenerate(rec.contact_id)}
                  className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500"
                >
                  Generate & Queue
                </button>
                <button
                  onClick={() => handleSkip(rec.contact_id)}
                  className="px-3 py-1.5 text-sm text-slate-500 border border-slate-600 rounded-lg hover:bg-slate-700"
                >
                  Skip
                </button>
              </div>

              {/* Inline Generate */}
              {activeGenId === rec.contact_id && (
                <div className="mt-4 pt-4 border-t border-slate-700">
                  <div className="flex gap-3 mb-3">
                    <select
                      value={genPurpose}
                      onChange={(e) => setGenPurpose(e.target.value)}
                      className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200"
                    >
                      {purposes.map((p) => (
                        <option key={p.id} value={p.id}>{p.id}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleGenerate(rec.contact_id)}
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
                            selectedVariation === i
                              ? "border-blue-500 bg-blue-500/10"
                              : "border-slate-600 hover:bg-slate-700"
                          }`}
                        >
                          <p className="text-slate-200 whitespace-pre-wrap">{variation}</p>
                        </button>
                      ))}

                      {selectedVariation !== null && !queueSuccess && (
                        <button
                          onClick={() => handleAddToQueue(rec)}
                          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500"
                        >
                          Add to Queue
                        </button>
                      )}
                      {queueError && <p className="text-sm text-red-400">{queueError}</p>}
                      {queueSuccess && (
                        <p className="text-sm text-green-400">
                          Added to queue! <Link to="/queue" className="underline">View queue</Link>
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
