"use client";
import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Diagnostics { status_counts: Record<string, number>; stuck_jobs: Array<{ job_id: string; status: string; current_stage: string | null; video_title: string; video_url: string; updated_at: string | null; retry_count: number; error_message: string | null; }>; stuck_count: number; }

const PIPELINE_STAGES = [
  { key: "ingestion", label: "1. Ingest", desc: "Fetch video metadata, create DB records" },
  { key: "audio_extraction", label: "2. Audio", desc: "Download audio, convert to WAV 16kHz" },
  { key: "transcription", label: "3. Transcribe", desc: "YouTube subs or Whisper ASR" },
  { key: "extraction", label: "4. Extract", desc: "LLM extracts price, rooms, location" },
  { key: "geocoding", label: "5. Geocode", desc: "Map to GPS, index in Meilisearch" },
];

export default function PipelinePage() {
  const [diag, setDiag] = useState<Diagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => { setLoading(true); const r = await fetch(`${API}/api/v1/pipeline/admin/diagnostics`); if (r.ok) setDiag(await r.json()); setLoading(false); }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (path: string) => {
    const r = await fetch(`${API}${path}`, { method: "POST" });
    if (r.ok) { const d = await r.json(); setMsg(JSON.stringify(d)); load(); }
  };

  const sc: Record<string, string> = { pending: "bg-sand-200 text-sand-600", ingesting: "bg-blue-100 text-blue-700", transcribing: "bg-purple-100 text-purple-700", extracting: "bg-aqar-100 text-aqar-700", geocoding: "bg-teal-100 text-teal-700", completed: "bg-emerald-100 text-emerald-700", failed: "bg-red-100 text-red-700", skipped: "bg-sand-200 text-sand-500" };

  if (loading) return <div className="mx-auto max-w-6xl py-12 text-center text-sand-400">Loading...</div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="mb-2 text-2xl font-bold text-sand-900">Pipeline Control</h1>

      {/* Pipeline flow explanation */}
      <div className="mb-6 rounded-xl border border-sea-200 bg-sea-50 p-4">
        <h2 className="mb-3 text-sm font-semibold text-sea-800">How the Pipeline Works</h2>
        <div className="flex flex-wrap gap-1">
          {PIPELINE_STAGES.map((s, i) => (
            <div key={s.key} className="flex items-center gap-1">
              <div className="rounded-lg bg-white border border-sea-200 px-3 py-2 text-center min-w-[120px]">
                <p className="text-xs font-bold text-sea-700">{s.label}</p>
                <p className="text-[10px] text-sand-500">{s.desc}</p>
              </div>
              {i < PIPELINE_STAGES.length - 1 && <span className="text-sea-400 text-lg">→</span>}
            </div>
          ))}
          <div className="flex items-center gap-1">
            <span className="text-sea-400 text-lg">→</span>
            <div className="rounded-lg bg-emerald-100 border border-emerald-200 px-3 py-2 text-center">
              <p className="text-xs font-bold text-emerald-700">✅ Done</p>
              <p className="text-[10px] text-sand-500">Published & searchable</p>
            </div>
          </div>
        </div>
        <p className="mt-2 text-xs text-sand-500">Each video goes through all 5 stages automatically. If a stage fails, the job is retried up to 3 times. You can also retry manually from any stage.</p>
      </div>

      {msg && <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700 break-all">{msg}<button onClick={() => setMsg("")} className="ml-2 font-bold">x</button></div>}

      {/* Status overview */}
      {diag && (
        <div className="mb-6 grid gap-3 grid-cols-4 lg:grid-cols-8">
          {Object.entries(diag.status_counts).map(([status, count]) => (
            <div key={status} className="rounded-lg border border-sand-200 bg-white p-3 text-center">
              <p className="text-xl font-bold text-sand-900">{count}</p>
              <p className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs capitalize ${sc[status] || ""}`}>{status}</p>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mb-6 flex gap-3 flex-wrap">
        <button onClick={() => act("/api/v1/pipeline/admin/retry-all-stuck")} className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600">Retry Stuck ({diag?.stuck_count || 0})</button>
        <button onClick={() => act("/api/v1/pipeline/admin/reset-failed")} className="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600">Reset Failed</button>
        <button onClick={() => act("/api/v1/pipeline/admin/discover-now")} className="rounded-lg bg-sea-500 px-4 py-2 text-sm font-medium text-white hover:bg-sea-600">Run Full Discovery</button>
        <button onClick={load} className="rounded-lg bg-sand-200 px-4 py-2 text-sm font-medium text-sand-700 hover:bg-sand-300">Refresh</button>
        <a href="http://localhost:5555" target="_blank" rel="noopener noreferrer" className="rounded-lg bg-purple-500 px-4 py-2 text-sm font-medium text-white hover:bg-purple-600">Open Flower</a>
      </div>

      {/* Stuck jobs */}
      {diag && diag.stuck_jobs.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-3 text-lg font-semibold text-red-600">Stuck Jobs ({diag.stuck_count})</h2>
          <div className="space-y-2">
            {diag.stuck_jobs.map((j) => (
              <div key={j.job_id} className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-sand-900 text-sm">{j.video_title}</p>
                  <p className="text-xs text-sand-500">{j.status} | {j.current_stage || "?"} | retries: {j.retry_count} {j.error_message && `| ${j.error_message.substring(0, 100)}`}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => act(`/api/v1/pipeline/admin/retry/${j.job_id}${j.current_stage ? `?from_stage=${j.current_stage}` : ""}`)} className="rounded bg-amber-500 px-2.5 py-1 text-xs text-white hover:bg-amber-600">Retry</button>
                  <button onClick={() => act(`/api/v1/pipeline/admin/cancel/${j.job_id}`)} className="rounded bg-red-500 px-2.5 py-1 text-xs text-white hover:bg-red-600">Cancel</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
