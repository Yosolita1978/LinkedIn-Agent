import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchContactDetail } from "../api/contacts";
import { generateMessage, fetchPurposes } from "../api/generate";
import { addToQueue } from "../api/queue";
import type { ContactDetail, Purpose, GenerateResponse } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import SegmentBadge from "../components/SegmentBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

export default function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [contact, setContact] = useState<ContactDetail | null>(null);
  const [purposes, setPurposes] = useState<Purpose[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Generate state
  const [selectedPurpose, setSelectedPurpose] = useState("reconnect");
  const [customContext, setCustomContext] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);
  const [selectedVariation, setSelectedVariation] = useState<number | null>(null);

  // Queue state
  const [queueing, setQueueing] = useState(false);
  const [queueSuccess, setQueueSuccess] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  function loadData() {
    if (!id) return;
    setLoading(true);
    setError(null);

    Promise.all([fetchContactDetail(id), fetchPurposes()])
      .then(([contactData, purposeData]) => {
        setContact(contactData);
        setPurposes(purposeData.purposes);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, [id]);

  function handleGenerate() {
    if (!id) return;
    setGenerating(true);
    setGenError(null);
    setGenResult(null);
    setSelectedVariation(null);
    setQueueSuccess(false);

    generateMessage({
      contact_id: id,
      purpose: selectedPurpose,
      custom_context: customContext || undefined,
      num_variations: 2,
    })
      .then((result) => {
        setGenResult(result);
        if (result.variations.length > 0) setSelectedVariation(0);
      })
      .catch((err) => setGenError(err.message))
      .finally(() => setGenerating(false));
  }

  function handleAddToQueue() {
    if (!contact || selectedVariation === null || !genResult) return;

    const segment = contact.segment_tags?.[0];
    const useCase = segment === "mujertech" ? "mujertech"
      : segment === "cascadia" ? "cascadia"
      : "job_search";

    setQueueing(true);
    setQueueError(null);

    addToQueue({
      contact_id: contact.id,
      use_case: useCase,
      outreach_type: contact.resurrection_opportunities.length > 0 ? "resurrection" : "warm",
      purpose: selectedPurpose,
      generated_message: genResult.variations[selectedVariation],
    })
      .then(() => setQueueSuccess(true))
      .catch((err) => setQueueError(err.message))
      .finally(() => setQueueing(false));
  }

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;
  if (!contact) return null;

  const meta = contact.message_metadata;
  const breakdown = contact.warmth_breakdown;

  return (
    <div>
      <Link to="/contacts" className="text-sm text-blue-400 hover:text-blue-300 mb-4 inline-block">
        &larr; Back to Contacts
      </Link>

      {/* Header */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{contact.name}</h1>
            <p className="text-slate-400 mt-1">
              {[contact.position, contact.company].filter(Boolean).join(" at ") || contact.headline || ""}
            </p>
            {contact.location && <p className="text-sm text-slate-500 mt-0.5">{contact.location}</p>}
            {contact.linkedin_url && (
              <a
                href={contact.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                Open LinkedIn
              </a>
            )}
          </div>
          <WarmthBadge score={contact.warmth_score} size="lg" />
        </div>

        <div className="flex gap-2 mt-3">
          {contact.segment_tags?.map((seg) => <SegmentBadge key={seg} segment={seg} />)}
        </div>

        {contact.about && (
          <p className="text-sm text-slate-400 mt-4 border-t border-slate-700 pt-4">{contact.about}</p>
        )}
      </div>

      {/* Warmth Breakdown */}
      {breakdown && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
          <h2 className="text-sm font-medium text-slate-400 mb-3">Warmth Breakdown</h2>
          <div className="space-y-2">
            <BreakdownBar label="Recency" value={breakdown.recency} max={30} color="bg-red-500" />
            <BreakdownBar label="Frequency" value={breakdown.frequency} max={20} color="bg-orange-500" />
            <BreakdownBar label="Depth" value={breakdown.depth} max={25} color="bg-blue-500" />
            <BreakdownBar label="Responsiveness" value={breakdown.responsiveness} max={15} color="bg-green-500" />
            <BreakdownBar label="Initiation" value={breakdown.initiation} max={10} color="bg-purple-500" />
          </div>
        </div>
      )}

      {/* Message Stats */}
      {meta && meta.total_messages > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
          <h2 className="text-sm font-medium text-slate-400 mb-3">Messages</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xl font-bold text-white">{meta.total_messages}</p>
              <p className="text-xs text-slate-500">Total</p>
            </div>
            <div>
              <p className="text-xl font-bold text-white">{meta.messages_sent}</p>
              <p className="text-xs text-slate-500">Sent</p>
            </div>
            <div>
              <p className="text-xl font-bold text-white">{meta.messages_received}</p>
              <p className="text-xs text-slate-500">Received</p>
            </div>
          </div>
          {meta.last_message_date && (
            <p className="text-xs text-slate-500 mt-3 text-center">
              Last message: {new Date(meta.last_message_date).toLocaleDateString()}
              {meta.last_message_direction && ` (${meta.last_message_direction})`}
            </p>
          )}
        </div>
      )}

      {/* Resurrection Opportunities */}
      {contact.resurrection_opportunities.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
          <h2 className="text-sm font-medium text-slate-400 mb-3">Outreach Opportunities</h2>
          <div className="space-y-2">
            {contact.resurrection_opportunities.filter(o => o.is_active).map((opp) => (
              <div key={opp.id} className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <p className="text-xs font-medium text-amber-400 capitalize mb-1">
                  {opp.hook_type.replace("_", " ")}
                </p>
                {opp.hook_detail && <p className="text-sm text-slate-300">{opp.hook_detail}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate Message */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Generate Message</h2>

        <div className="flex flex-wrap gap-3 mb-3">
          <select
            value={selectedPurpose}
            onChange={(e) => setSelectedPurpose(e.target.value)}
            className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200"
          >
            {purposes.map((p) => (
              <option key={p.id} value={p.id}>{p.id} — {p.description}</option>
            ))}
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {generating ? "Generating..." : "Generate"}
          </button>
        </div>

        <textarea
          placeholder="Optional: add custom context..."
          value={customContext}
          onChange={(e) => setCustomContext(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {genError && <ErrorMessage message={genError} />}

        {genResult && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500">
              {genResult.variations.length} variation(s) — {genResult.tokens_used} tokens used
            </p>
            {genResult.variations.map((variation, i) => (
              <button
                key={i}
                onClick={() => setSelectedVariation(i)}
                className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                  selectedVariation === i
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-slate-600 hover:bg-slate-700"
                }`}
              >
                <p className="text-xs text-slate-500 mb-1">Variation {i + 1}</p>
                <p className="text-slate-200 whitespace-pre-wrap">{variation}</p>
              </button>
            ))}

            {selectedVariation !== null && !queueSuccess && (
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleAddToQueue}
                  disabled={queueing}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 disabled:opacity-50"
                >
                  {queueing ? "Adding..." : "Add to Queue"}
                </button>
                {queueError && <span className="text-sm text-red-400">{queueError}</span>}
              </div>
            )}

            {queueSuccess && (
              <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                <p className="text-sm text-green-400">
                  Added to queue! <Link to="/queue" className="underline">View queue</Link>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function BreakdownBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-500 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-3 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-10 text-right">{value}/{max}</span>
    </div>
  );
}
