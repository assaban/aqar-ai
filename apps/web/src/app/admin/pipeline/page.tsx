"use client";

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Diagnostics {
  status_counts: Record<string, number>;
  stuck_jobs: Array<{
    job_id: string;
    status: string;
    current_stage: string | null;
    video_title: string;
    video_url: string;
    updated_at: string | null;
    retry_count: number;
    error_message: string | null;
  }>;
  stuck_count: number;
}

export default function AdminPipelinePage() {
  const [diag, setDiag] = useState<Diagnostics | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const [diagRes, jobsRes] = await Promise.all([
      fetch(`${API}/api/v1/pipeline/admin/diagnostics`),
      fetch(`${API}/api/v1/pipeline/jobs?limit=20`),
    ]);
    if (diagRes.ok) setDiag(await diagRes.json());
    if (jobsRes.ok) setJobs(await jobsRes.json());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const retryJob = async (jobId: string, stage?: string) => {
    const url = stage
      ? `${API}/api/v1/pipeline/admin/retry/${jobId}?from_stage=${stage}`
      : `${API}/api/v1/pipeline/admin/retry/${jobId}`;
    const res = await fetch(url, { method: "POST" });
    if (res.ok) { setMsg("Job retried"); load(); }
  };

  const cancelJob = async (jobId: string) => {
    const res = await fetch(`${API}/api/v1/pipeline/admin/cancel/${jobId}`, { method: "POST" });
    if (res.ok) { setMsg("Job cancelled"); load(); }
  };

  const retryAllStuck = async () => {
    const res = await fetch(`${API}/api/v1/pipeline/admin/retry-all-stuck`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setMsg(`Retried ${data.retried_count} stuck jobs`);
      load();
    }
  };

  const resetFailed = async () => {
    const res = await fetch(`${API}/api/v1/pipeline/admin/reset-failed`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setMsg(`Reset ${data.reset_count} failed jobs`);
      load();
    }
  };

  const statusColor: Record<string, string> = {
    pending: "bg-sand-200 text-sand-600",
    ingesting: "bg-blue-100 text-blue-700",
    transcribing: "bg-purple-100 text-purple-700",
    extracting: "bg-aqar-100 text-aqar-700",
    geocoding: "bg-teal-100 text-teal-700",
    completed: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
    skipped: "bg-sand-200 text-sand-500",
  };

  if (loading) return <div className="mx-auto max-w-6xl px-4 py-12 text-center text-sand-400">Loading pipeline data...</div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="mb-6 text-2xl font-bold text-sand-900">Pipeline Control</h1>

      {msg && (
        <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">
          {msg}<button onClick={() => setMsg("")} className="ml-2 text-sea-500">x</button>
        </div>
      )}

      {/* Status overview */}
      {diag && (
        <div className="mb-6 grid gap-3 sm:grid-cols-4 lg:grid-cols-8">
          {Object.entries(diag.status_counts).map(([status, count]) => (
            <div key={status} className="rounded-lg border border-sand-200 bg-white p-3 text-center">
              <p className="text-xl font-bold text-sand-900">{count}</p>
              <p className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs capitalize ${statusColor[status] || ""}`}>{status}</p>
            </div>
          ))}
        </div>
      )}

      {/* Bulk actions */}
      <div className="mb-6 flex gap-3">
        <button onClick={retryAllStuck}
          className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600">
          Retry All Stuck ({diag?.stuck_count || 0})
        </button>
        <button onClick={resetFailed}
          className="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600">
          Reset All Failed
        </button>
        <button onClick={load}
          className="rounded-lg bg-sand-200 px-4 py-2 text-sm font-medium text-sand-700 hover:bg-sand-300">
          Refresh
        </button>
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
                  <p className="text-xs text-sand-500">
                    {j.status} | {j.current_stage || "no stage"} | retries: {j.retry_count}
                    {j.error_message && ` | ${j.error_message.substring(0, 80)}...`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => retryJob(j.job_id, j.current_stage || undefined)}
                    className="rounded bg-amber-500 px-2.5 py-1 text-xs text-white hover:bg-amber-600">Retry</button>
                  <button onClick={() => cancelJob(j.job_id)}
                    className="rounded bg-red-500 px-2.5 py-1 text-xs text-white hover:bg-red-600">Cancel</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent jobs */}
      <h2 className="mb-3 text-lg font-semibold text-sand-900">Recent Jobs</h2>
      <div className="overflow-x-auto rounded-xl border border-sand-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sand-100 text-xs text-sand-400">
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Stage</th>
              <th className="px-4 py-3 font-medium">Retries</th>
              <th className="px-4 py-3 font-medium">Error</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j: any) => (
              <tr key={j.job_id || j.id} className="border-b border-sand-50 hover:bg-sand-50">
                <td className="px-4 py-2.5">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[j.status] || ""}`}>{j.status}</span>
                </td>
                <td className="px-4 py-2.5 text-sand-600">{j.current_stage || "-"}</td>
                <td className="px-4 py-2.5 text-sand-600">{j.retry_count || 0}</td>
                <td className="px-4 py-2.5 text-xs text-red-500 max-w-xs truncate">{j.error_message || "-"}</td>
                <td className="px-4 py-2.5">
                  {j.status !== "completed" && j.status !== "skipped" && (
                    <div className="flex gap-1">
                      <button onClick={() => retryJob(j.job_id || j.id)}
                        className="rounded bg-amber-500 px-2 py-0.5 text-xs text-white hover:bg-amber-600">Retry</button>
                      <button onClick={() => cancelJob(j.job_id || j.id)}
                        className="rounded bg-sand-300 px-2 py-0.5 text-xs text-sand-700 hover:bg-sand-400">Cancel</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
