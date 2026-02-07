import { useEffect, useState } from "react";
import {
  fetchTargetCompanies,
  addTargetCompany,
  addTargetCompaniesBulk,
  deleteTargetCompany,
} from "../api/targetCompanies";
import type { TargetCompany } from "../api/targetCompanies";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

export default function TargetCompaniesPage() {
  const [companies, setCompanies] = useState<TargetCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add single company
  const [newName, setNewName] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Bulk add
  const [bulkText, setBulkText] = useState("");
  const [bulkAdding, setBulkAdding] = useState(false);
  const [bulkResult, setBulkResult] = useState<string | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);

  // Delete
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function loadCompanies() {
    setLoading(true);
    setError(null);

    fetchTargetCompanies()
      .then((data) => setCompanies(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadCompanies(); }, []);

  async function handleAdd() {
    if (!newName.trim()) return;
    setAdding(true);
    setAddError(null);

    try {
      await addTargetCompany({ name: newName.trim(), notes: newNotes.trim() || null });
      setNewName("");
      setNewNotes("");
      loadCompanies();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add company");
    } finally {
      setAdding(false);
    }
  }

  async function handleBulkAdd() {
    const names = bulkText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    if (names.length === 0) return;

    setBulkAdding(true);
    setBulkError(null);
    setBulkResult(null);

    try {
      const result = await addTargetCompaniesBulk(
        names.map((name) => ({ name }))
      );
      setBulkResult(`Added ${result.created} companies (${result.skipped} already existed)`);
      setBulkText("");
      loadCompanies();
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : "Bulk add failed");
    } finally {
      setBulkAdding(false);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await deleteTargetCompany(id);
      loadCompanies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Target Companies</h1>
      <p className="text-sm text-slate-400 mb-6">
        Add companies you're interested in for your job search. Contacts working at these companies
        will be tagged as "Job Target" when you run segmentation.
      </p>

      {/* Add Single Company */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Add Company</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Company name (e.g. Google)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
            className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={newNotes}
            onChange={(e) => setNewNotes(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
            className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleAdd}
            disabled={adding || !newName.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {adding ? "Adding..." : "Add"}
          </button>
        </div>
        {addError && <p className="text-sm text-red-400 mt-2">{addError}</p>}
      </div>

      {/* Bulk Add */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-400 mb-3">Bulk Add (one company per line)</h2>
        <textarea
          placeholder={"Google\nMeta\nAmazon\nMicrosoft\nApple"}
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          rows={5}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 placeholder-slate-500 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleBulkAdd}
          disabled={bulkAdding || !bulkText.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
        >
          {bulkAdding ? "Adding..." : "Add All"}
        </button>
        {bulkResult && (
          <p className="text-sm text-green-400 mt-2">{bulkResult}</p>
        )}
        {bulkError && <p className="text-sm text-red-400 mt-2">{bulkError}</p>}
      </div>

      {error && <ErrorMessage message={error} onRetry={loadCompanies} />}
      {loading && <LoadingSpinner />}

      {!loading && !error && companies.length === 0 && (
        <EmptyState
          title="No target companies"
          description="Add companies above to start tagging contacts for your job search"
        />
      )}

      {!loading && !error && companies.length > 0 && (
        <div className="bg-slate-800 rounded-lg border border-slate-700">
          <div className="px-4 py-3 border-b border-slate-700">
            <p className="text-xs text-slate-500">{companies.length} target companies</p>
          </div>
          <div className="divide-y divide-slate-700">
            {companies.map((company) => (
              <div key={company.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-200">{company.name}</p>
                  {company.notes && (
                    <p className="text-xs text-slate-500 mt-0.5">{company.notes}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(company.id)}
                  disabled={deletingId === company.id}
                  className="px-3 py-1.5 text-sm text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 disabled:opacity-50"
                >
                  {deletingId === company.id ? "..." : "Delete"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
