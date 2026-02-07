import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchContactStats, fetchTopWarmth } from "../api/contacts";
import { fetchQueueStats } from "../api/queue";
import { fetchOpportunities } from "../api/resurrection";
import { fetchRecommendations } from "../api/ranking";
import type { ContactStats, TopWarmthContact, QueueStats, Recommendation } from "../types";
import WarmthBadge from "../components/WarmthBadge";
import PriorityBadge from "../components/PriorityBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

export default function DashboardPage() {
  const [stats, setStats] = useState<ContactStats | null>(null);
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
      fetchContactStats(),
      fetchTopWarmth(10),
      fetchQueueStats(),
      fetchOpportunities(),
      fetchRecommendations(5),
    ])
      .then(([statsData, topData, queueData, oppData, recData]) => {
        setStats(statsData);
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
  if (!stats) return null;

  const warmthDist = stats.warmth_distribution;
  const warmthTotal = warmthDist.hot + warmthDist.warm + warmthDist.cool + warmthDist.cold + warmthDist.none;

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard label="Total Contacts" value={stats.total_contacts} />
        <StatCard label="With Messages" value={stats.contacts_with_messages} />
        <StatCard label="Avg Warmth" value={Math.round(stats.average_warmth)} />
        <StatCard label="Queue Drafts" value={queueStats?.by_status?.draft ?? 0} />
        <StatCard label="Opportunities" value={opportunityCount} />
      </div>

      {/* Warmth Distribution */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-8">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Warmth Distribution</h2>
        {warmthTotal > 0 && (
          <div className="flex rounded-full overflow-hidden h-4 mb-2 bg-slate-700">
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
        <div className="flex gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500" />Hot: {warmthDist.hot}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-orange-500" />Warm: {warmthDist.warm}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-blue-500" />Cool: {warmthDist.cool}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-500" />Cold: {warmthDist.cold}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-700 border border-slate-600" />None: {warmthDist.none}</span>
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
      <div className="flex gap-3">
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

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value.toLocaleString()}</p>
    </div>
  );
}
