// Reusable conversion-funnel strip. Used by Today (Candidate → Requested →
// Accepted → Drafted → Sent → Responded) and Reactivate (Opportunity → Drafted
// → Sent → Responded). A stage with count === null renders as an explicit
// "not available yet" state — never a fabricated zero.

export interface FunnelStage {
  label: string;
  count: number | null;
  emphasis?: boolean; // the success stage (e.g. Responded)
}

export default function Funnel({ stages }: { stages: FunnelStage[] }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-stretch gap-2">
      {stages.map((stage, i) => (
        <div
          key={stage.label}
          className="flex flex-col sm:flex-row sm:items-stretch sm:flex-1"
        >
          <div
            className={`flex-1 rounded-lg border p-4 text-center ${
              stage.emphasis
                ? "border-emerald-500/40 bg-emerald-500/10"
                : "border-slate-700 bg-slate-800"
            }`}
          >
            {stage.count === null ? (
              <p className="text-2xl font-bold text-slate-600" title="Not available yet">
                —
              </p>
            ) : (
              <p
                className={`text-2xl font-bold ${
                  stage.emphasis ? "text-emerald-400" : "text-white"
                }`}
              >
                {stage.count}
              </p>
            )}
            <p className="text-xs text-slate-400 mt-1">{stage.label}</p>
            {stage.count === null && (
              <p className="text-[10px] text-slate-600 mt-0.5">not available yet</p>
            )}
          </div>

          {i < stages.length - 1 && (
            <div className="flex items-center justify-center px-1 text-slate-600">
              {/* chevron points down on mobile (stacked), right on desktop (row) */}
              <svg
                className="w-5 h-5 rotate-90 sm:rotate-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
