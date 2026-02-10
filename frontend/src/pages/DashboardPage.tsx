import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchTopWarmth } from "../api/contacts";
import { fetchQueueStats } from "../api/queue";
import { fetchOpportunities } from "../api/resurrection";
import { fetchRecommendations } from "../api/ranking";
import { fetchNetworkOverview } from "../api/analytics";
import type { NetworkOverview, TopWarmthContact, QueueStats, Recommendation } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import PriorityBadge from "../components/PriorityBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

const SEGMENT_LABELS: Record<string, string> = {
  mujertech: "MujerTech",
  cascadia: "Cascadia AI",
  job_target: "Job Target",
  untagged: "Untagged",
};

const SEGMENT_COLORS: Record<string, string> = {
  mujertech: "bg-pink-500",
  cascadia: "bg-cyan-500",
  job_target: "bg-amber-500",
  untagged: "bg-slate-600",
};

export default function DashboardPage() {
  const [overview, setOverview] = useState<NetworkOverview | null>(null);
  const [topContacts, setTopContacts] = useState<TopWarmthContact[]>([]);
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [opportunityCount, setOpportunityCount] = useState<number>(0);
  const [topRecs, setTopRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadData() {
    setLoading(true);
    setError(null);

    Promise.all([
      fetchNetworkOverview(),
      fetchTopWarmth(10),
      fetchQueueStats(),
      fetchOpportunities(),
      fetchRecommendations(5),
    ])
      .then(([overviewData, topData, queueData, oppData, recData]) => {
        setOverview(overviewData);
        setTopContacts(topData);
        setQueueStats(queueData);
        setOpportunityCount(oppData.count);
        setTopRecs(recData.recommendations);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} onRetry={loadData} />;
  if (!overview) return null;

  const warmthDist = overview.warmth_distribution;
  const warmthTotal = warmthDist.hot + warmthDist.warm + warmthDist.cool + warmthDist.cold + warmthDist.none;
  const segmentTotal = Object.values(overview.segments).reduce((sum, s) => sum + s.count, 0);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
        <StatCard
          label="Total Contacts"
          value={overview.totals.contacts}
          tooltip="All LinkedIn connections imported into the system"
          to="/contacts"
        />
        <StatCard
          label="With Messages"
          value={overview.totals.with_messages}
          tooltip="Contacts who have exchanged at least one message with you"
          to="/contacts"
        />
        <StatCard
          label="Companies"
          value={overview.totals.unique_companies}
          tooltip="Unique companies across your network"
        />
        <StatCard
          label="Senior Contacts"
          value={overview.totals.senior_contacts}
          subtext={`${overview.totals.senior_pct}% of network`}
          tooltip="VPs, Directors, C-suite, Founders, Partners, and other senior leaders"
        />
        <StatCard
          label="Queue Drafts"
          value={queueStats?.by_status?.draft ?? 0}
          tooltip="Messages drafted and waiting for your review before sending"
          to="/queue"
        />
        <StatCard
          label="Opportunities"
          value={opportunityCount}
          tooltip="Dormant contacts with re-engagement hooks — good moment to reconnect"
          to="/opportunities"
        />
      </div>

      {/* Network Archetype */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-medium text-slate-400">Network Archetype</h2>
          <span className="text-xs text-slate-500">Avg Warmth: {overview.average_warmth}</span>
        </div>
        <div className="flex items-start gap-4">
          <span className="text-lg font-bold text-emerald-400 shrink-0">
            {overview.archetype.archetype}
          </span>
          <div>
            <p className="text-sm text-slate-300">{overview.archetype.description}</p>
            <p className="text-xs text-slate-500 mt-1">{overview.archetype.strategy}</p>
          </div>
        </div>
      </div>

      {/* Warmth Distribution + Segment Distribution side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        {/* Warmth Distribution */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h2 className="text-sm font-medium text-slate-400 mb-3">Warmth Distribution</h2>
          {warmthTotal > 0 && (
            <div className="flex rounded-full overflow-hidden h-4 mb-3 bg-slate-700">
              {warmthDist.hot > 0 && (
                <div className="bg-red-500" style={{ width: `${(warmthDist.hot / warmthTotal) * 100}%` }} title={`Hot: ${warmthDist.hot}`} />
              )}
              {warmthDist.warm > 0 && (
                <div className="bg-orange-500" style={{ width: `${(warmthDist.warm / warmthTotal) * 100}%` }} title={`Warm: ${warmthDist.warm}`} />
              )}
              {warmthDist.cool > 0 && (
                <div className="bg-blue-500" style={{ width: `${(warmthDist.cool / warmthTotal) * 100}%` }} title={`Cool: ${warmthDist.cool}`} />
              )}
              {warmthDist.cold > 0 && (
                <div className="bg-slate-500" style={{ width: `${(warmthDist.cold / warmthTotal) * 100}%` }} title={`Cold: ${warmthDist.cold}`} />
              )}
              {warmthDist.none > 0 && (
                <div className="bg-slate-700" style={{ width: `${(warmthDist.none / warmthTotal) * 100}%` }} title={`None: ${warmthDist.none}`} />
              )}
            </div>
          )}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500" />Hot: {warmthDist.hot}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-orange-500" />Warm: {warmthDist.warm}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-blue-500" />Cool: {warmthDist.cool}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" />Cold: {warmthDist.cold}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-700 border border-slate-600" />None: {warmthDist.none}</span>
          </div>
        </div>

        {/* Segment Distribution */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h2 className="text-sm font-medium text-slate-400 mb-3">Audience Segments</h2>
          {segmentTotal > 0 && (
            <div className="flex rounded-full overflow-hidden h-4 mb-3 bg-slate-700">
              {Object.entries(overview.segments).map(([key, seg]) =>
                seg.count > 0 ? (
                  <div
                    key={key}
                    className={SEGMENT_COLORS[key] ?? "bg-slate-600"}
                    style={{ width: `${(seg.count / segmentTotal) * 100}%` }}
                    title={`${SEGMENT_LABELS[key] ?? key}: ${seg.count}`}
                  />
                ) : null
              )}
            </div>
          )}
          <div className="space-y-1.5">
            {Object.entries(overview.segments).map(([key, seg]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-slate-400">
                  <span className={`w-2.5 h-2.5 rounded-full ${SEGMENT_COLORS[key] ?? "bg-slate-600"}`} />
                  {SEGMENT_LABELS[key] ?? key}
                </span>
                <span className="text-slate-500">
                  {seg.count} contacts &middot; avg warmth {seg.average_warmth}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Companies */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-8">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Top Companies in Your Network</h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
          {overview.top_companies.map((company) => {
            const maxCount = overview.top_companies[0]?.count ?? 1;
            const pct = (company.count / maxCount) * 100;
            return (
              <div key={company.company} className="relative overflow-hidden rounded bg-slate-700/50 px-3 py-2">
                <div
                  className="absolute inset-y-0 left-0 bg-blue-500/15"
                  style={{ width: `${pct}%` }}
                />
                <div className="relative">
                  <p className="text-xs font-medium text-slate-300 truncate">{company.company}</p>
                  <p className="text-xs text-slate-500">{company.count} contacts</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Today's Top Outreach */}
      {topRecs.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-slate-400">Today's Top Outreach</h2>
            <Link to="/recommendations" className="text-sm text-blue-400 hover:text-blue-300">View all</Link>
          </div>
          <div className="divide-y divide-slate-700">
            {topRecs.map((rec) => (
              <Link
                key={rec.contact_id}
                to={`/contacts/${rec.contact_id}`}
                className="flex items-center justify-between py-2 hover:bg-slate-700/50 -mx-2 px-2 rounded"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{rec.contact_name}</p>
                  <p className="text-xs text-slate-500 truncate">
                    {rec.reasons[0] ?? rec.contact_company ?? ""}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <WarmthBadge score={rec.warmth_score} size="sm" />
                  <PriorityBadge score={rec.priority_score} size="sm" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Top Warmth Contacts */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-slate-400">Top 10 Warmest Contacts</h2>
          <Link to="/contacts" className="text-sm text-blue-400 hover:text-blue-300">View all</Link>
        </div>
        <div className="divide-y divide-slate-700">
          {topContacts.map((contact) => (
            <Link
              key={contact.id}
              to={`/contacts/${contact.id}`}
              className="flex items-center justify-between py-2 hover:bg-slate-700/50 -mx-2 px-2 rounded"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{contact.name}</p>
                <p className="text-xs text-slate-500 truncate">{contact.company ?? contact.headline ?? ""}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-4">
                <span className="text-xs text-slate-500">{contact.total_messages} msgs</span>
                <WarmthBadge score={contact.warmth_score} />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link to="/recommendations" className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-500">
          Today's Outreach
        </Link>
        <Link to="/contacts" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500">
          View Contacts
        </Link>
        <Link to="/queue" className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-700">
          Review Queue
        </Link>
        <Link to="/opportunities" className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-700">
          See Opportunities
        </Link>
      </div>
    </div>
  );
}

function StatCard({ label, value, subtext, tooltip, to }: {
  label: string;
  value: number;
  subtext?: string;
  tooltip?: string;
  to?: string;
}) {
  const navigate = useNavigate();

  return (
    <div
      className={`bg-slate-800 rounded-lg border border-slate-700 p-4 ${to ? "cursor-pointer hover:border-slate-500 hover:bg-slate-750 transition-colors" : ""}`}
      onClick={to ? () => navigate(to) : undefined}
    >
      <div className="flex items-center gap-1 mb-1">
        <p className="text-xs text-slate-500">{label}</p>
        {tooltip && (
          <div className="relative group">
            <span className="text-slate-600 hover:text-slate-400 cursor-help text-xs">?</span>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-xs text-slate-300 w-52 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-lg">
              {tooltip}
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-600" />
            </div>
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
      {subtext && <p className="text-[10px] text-slate-500 mt-0.5">{subtext}</p>}
      {to && <p className="text-[10px] text-slate-600 mt-1">Click to view</p>}
    </div>
  );
}
