import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { fetchSettings, updateSettings } from "../api/settings";
import type { AppSettings } from "../types";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

// The persona fields drive the connection-note writer (People to Convert): the
// bio and interests are "your side" of the common ground the notes open with.
export default function SettingsPage() {
  const [form, setForm] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function loadSettings() {
    setLoading(true);
    setError(null);
    fetchSettings()
      .then((data) => setForm(data))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadSettings(); }, []);

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
    setSaved(false);
  }

  async function handleSave() {
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const result = await updateSettings(form);
      setForm(result);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
      <p className="text-slate-400 text-sm mb-6">
        Your persona drives the connection notes on{" "}
        <span className="text-slate-300">People to Convert</span> — the bio and
        interests are what the writer uses to find common ground with each person.
      </p>

      {error && <ErrorMessage message={error} onRetry={form ? undefined : loadSettings} />}

      {form && (
        <div className="space-y-6">
          {/* ── Persona ── */}
          <section className="bg-slate-800 rounded-lg border border-slate-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Your persona</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Name">
                <TextInput value={form.persona_name} onChange={(v) => update("persona_name", v)} />
              </Field>
              <Field label="Location">
                <TextInput value={form.persona_location} onChange={(v) => update("persona_location", v)} />
              </Field>
            </div>

            <Field label="Title">
              <TextInput value={form.persona_title} onChange={(v) => update("persona_title", v)} />
            </Field>

            <Field
              label="Bio"
              hint="A short paragraph about who you are, what you build, and the communities you're part of. The more specific, the better the 'we both…' hooks."
            >
              <textarea
                value={form.persona_bio}
                onChange={(e) => update("persona_bio", e.target.value)}
                rows={6}
                placeholder="e.g. AI Engineer and Technical Curriculum Developer in Seattle…"
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              />
            </Field>

            <Field
              label="Interests"
              hint="Comma-separated topics and communities you care about."
            >
              <TextInput
                value={form.persona_interests}
                onChange={(v) => update("persona_interests", v)}
              />
            </Field>
          </section>

          {/* ── Outreach ── */}
          <section className="bg-slate-800 rounded-lg border border-slate-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Outreach</h2>
            <Field
              label="Weekly request cap"
              hint="Your personal target for connection requests per week. Shown as the meter on the Today dashboard."
            >
              <input
                type="number"
                min={1}
                max={1000}
                value={form.weekly_request_cap}
                onChange={(e) => update("weekly_request_cap", Number(e.target.value))}
                className="w-32 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </Field>
          </section>

          {/* ── Save ── */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
            {saved && !saving && (
              <span className="text-sm text-emerald-400">Saved — applies to your next batch of notes.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

function TextInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  );
}
