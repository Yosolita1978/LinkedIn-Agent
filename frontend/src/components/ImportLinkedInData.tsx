import { useEffect, useRef, useState } from "react";
import {
  uploadConnections,
  uploadMessages,
  fetchUploadStatus,
  type UploadResult,
  type UploadStatus,
} from "../api/upload";

// Collapsible panel for importing LinkedIn's official data export
// (Connections.csv + messages.csv). messages.csv is what populates each
// contact's last-message date, which powers the "Reconnect (oldest first)" list.
export default function ImportLinkedInData({
  onImported,
  defaultOpen = false,
}: {
  onImported: () => void;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [status, setStatus] = useState<UploadStatus | null>(null);

  function loadStatus() {
    fetchUploadStatus().then(setStatus).catch(() => setStatus(null));
  }

  useEffect(() => { loadStatus(); }, []);

  function handleImported() {
    loadStatus();
    onImported();
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 mb-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div>
          <p className="text-sm font-medium text-white">Import LinkedIn data</p>
          <p className="text-xs text-slate-500">
            {status
              ? `${status.total_contacts} contacts · ${status.total_messages} messages imported`
              : "Upload your LinkedIn export to populate reconnections"}
          </p>
        </div>
        <svg
          className={`w-5 h-5 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-slate-700 pt-4 space-y-4">
          <p className="text-xs text-slate-400">
            On LinkedIn: <span className="text-slate-300">Settings &amp; Privacy → Data Privacy → Get a copy
            of your data</span>. Select <span className="text-slate-300">Connections</span> and{" "}
            <span className="text-slate-300">Messages</span>, request the archive, then upload the CSVs here.
            Messages are what let the tool sort by who you haven't talked to the longest.
          </p>

          <UploadRow
            label="messages.csv"
            hint="Populates last-contact dates → drives the oldest-first reconnect list."
            upload={uploadMessages}
            onDone={handleImported}
          />
          <UploadRow
            label="Connections.csv"
            hint="Adds/refreshes your connections (name, company, position, connected date)."
            upload={uploadConnections}
            onDone={handleImported}
          />
        </div>
      )}
    </div>
  );
}

function UploadRow({
  label,
  hint,
  upload,
  onDone,
}: {
  label: string;
  hint: string;
  upload: (file: File) => Promise<UploadResult>;
  onDone: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setFileName(file.name);
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await upload(file);
      setResult(res);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-700 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200">{label}</p>
          <p className="text-xs text-slate-500">{hint}</p>
        </div>
        <div className="shrink-0">
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
              e.target.value = ""; // allow re-selecting the same file
            }}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 whitespace-nowrap"
          >
            {busy ? "Uploading…" : "Choose CSV"}
          </button>
        </div>
      </div>

      {fileName && !busy && (result || error) && (
        <p className="text-xs text-slate-500 mt-2 truncate">{fileName}</p>
      )}

      {result && (
        <div className="mt-2 text-xs text-emerald-400">
          Processed {result.records_processed} rows
          {result.contacts_created > 0 && ` · ${result.contacts_created} contacts added`}
          {result.contacts_updated > 0 && ` · ${result.contacts_updated} updated`}
          {result.messages_created > 0 && ` · ${result.messages_created} messages`}
          {result.errors.length > 0 && (
            <span className="block text-amber-400 mt-1">
              {result.errors.length} row{result.errors.length !== 1 ? "s" : ""} had issues
            </span>
          )}
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  );
}
