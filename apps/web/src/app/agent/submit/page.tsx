"use client";

import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AgentSubmitPage() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const submit = async () => {
    if (!url.trim()) return;
    setStatus("loading");
    try {
      const res = await fetch(`${API}/api/v1/pipeline/submit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        setResult(await res.json());
        setStatus("success");
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || "Submission failed");
        setStatus("error");
      }
    } catch {
      setErrorMsg("Connection error. Please try again.");
      setStatus("error");
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <div className="mb-8 text-center">
        <div className="mb-3 text-4xl">📹</div>
        <h1 className="text-2xl font-bold text-sand-900">Submit a Property Video</h1>
        <p className="mt-2 text-sand-500">
          Paste a YouTube video URL of a property tour. Our AI will process it
          automatically: transcribe, extract details, and list the property.
        </p>
      </div>

      <div className="rounded-xl border border-sand-200 bg-white p-6">
        <label className="mb-2 block text-sm font-medium text-sand-700">YouTube Video URL</label>
        <div className="flex gap-3">
          <input value={url} onChange={(e) => { setUrl(e.target.value); setStatus("idle"); }}
            placeholder="https://www.youtube.com/watch?v=..."
            className="flex-1 rounded-lg border border-sand-200 px-4 py-3 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
            onKeyDown={(e) => e.key === "Enter" && submit()} />
          <button onClick={submit} disabled={status === "loading"}
            className="rounded-lg bg-aqar-500 px-6 py-3 font-semibold text-white hover:bg-aqar-600 disabled:opacity-50">
            {status === "loading" ? "Processing..." : "Submit"}
          </button>
        </div>

        {status === "error" && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
            {errorMsg}
          </div>
        )}

        {status === "success" && result && (
          <div className="mt-4 rounded-lg bg-emerald-50 border border-emerald-200 p-4">
            <p className="font-medium text-emerald-800">Video submitted successfully!</p>
            <p className="mt-1 text-sm text-emerald-600">
              Job ID: <code className="bg-emerald-100 px-1 rounded">{result.job_id}</code>
            </p>
            <p className="mt-1 text-sm text-sand-500">
              The video is being processed through our AI pipeline.
              This typically takes 2-5 minutes.
            </p>
            <div className="mt-3 flex gap-3">
              <button onClick={() => { setUrl(""); setStatus("idle"); setResult(null); }}
                className="rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">
                Submit Another
              </button>
              <Link href={`/stats`}
                className="rounded-lg bg-sand-200 px-4 py-2 text-sm font-medium text-sand-700 hover:bg-sand-300">
                View Dashboard
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* How it works */}
      <div className="mt-8 rounded-xl border border-sand-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-sand-900">How It Works</h2>
        <div className="space-y-3">
          {[
            { num: "1", title: "Submit URL", desc: "Paste your YouTube property tour video link" },
            { num: "2", title: "AI Transcription", desc: "Whisper transcribes the Arabic/Darija audio (or uses YouTube captions)" },
            { num: "3", title: "Data Extraction", desc: "LLM extracts price, area, rooms, location, and more" },
            { num: "4", title: "Geocoding", desc: "Location is mapped to GPS coordinates on the map" },
            { num: "5", title: "Published", desc: "Property appears in search results with all details" },
          ].map((s) => (
            <div key={s.num} className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-aqar-100 text-xs font-bold text-aqar-600">
                {s.num}
              </div>
              <div>
                <p className="text-sm font-medium text-sand-800">{s.title}</p>
                <p className="text-xs text-sand-500">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
