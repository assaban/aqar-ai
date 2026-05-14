"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SearchResult {
  channel_id: string;
  channel_name: string;
  channel_url: string;
  subscriber_count: string | null;
  video_count: string | null;
  description: string;
  already_registered: boolean;
}

const SUGGESTED_KEYWORDS = [
  "عقارات طنجة",
  "شقق للبيع طنجة",
  "immobilier tanger",
  "real estate tangier morocco",
  "بيع شراء طنجة تطوان",
  "villa tanger",
  "terrain tanger",
  "location appartement tanger",
];

export default function AdminDiscoverPage() {
  const [keywords, setKeywords] = useState("");
  const [maxResults, setMaxResults] = useState(15);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const search = async () => {
    if (!keywords.trim()) return;
    setLoading(true);
    setMsg("");
    try {
      const res = await fetch(`${API}/api/v1/channels/discover`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, max_results: maxResults }),
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data);
        setMsg(`Found ${data.length} unique channel(s)`);
      } else {
        setMsg("Search failed. Check worker logs.");
      }
    } catch {
      setMsg("Connection error");
    }
    setLoading(false);
  };

  const addChannel = async (result: SearchResult) => {
    const res = await fetch(`${API}/api/v1/channels`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel_url: result.channel_url,
        channel_name: result.channel_name,
        description: result.description,
        region: "tangier-tetouan",
      }),
    });
    if (res.ok) {
      setMsg(`Added: ${result.channel_name}. Go to Channels to approve.`);
      // Mark as registered in local state
      setResults(results.map(r =>
        r.channel_id === result.channel_id ? { ...r, already_registered: true } : r
      ));
    } else {
      const err = await res.json();
      setMsg(`Error: ${err.detail || "Failed to add"}`);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="mb-2 text-2xl font-bold text-sand-900">Discover YouTube Channels</h1>
      <p className="mb-6 text-sm text-sand-500">
        Search YouTube for real estate channels in the Tangier-Tetouan region. Add promising channels for monitoring.
      </p>

      {msg && (
        <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">
          {msg}<button onClick={() => setMsg("")} className="ml-2 text-sea-500">x</button>
        </div>
      )}

      {/* Search form */}
      <div className="mb-6 rounded-xl border border-sand-200 bg-white p-5">
        <div className="flex gap-3 mb-3">
          <input value={keywords} onChange={(e) => setKeywords(e.target.value)}
            placeholder="Search keywords (Arabic, French, or English)..."
            className="flex-1 rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
            onKeyDown={(e) => e.key === "Enter" && search()} />
          <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))}
            className="rounded-lg border border-sand-200 px-3 py-2.5 text-sm">
            <option value={10}>10 results</option>
            <option value={15}>15 results</option>
            <option value={25}>25 results</option>
            <option value={50}>50 results</option>
          </select>
          <button onClick={search} disabled={loading}
            className="rounded-lg bg-sea-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-sea-600 disabled:opacity-50">
            {loading ? "Searching..." : "Search YouTube"}
          </button>
        </div>

        {/* Suggested keywords */}
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs text-sand-400">Try:</span>
          {SUGGESTED_KEYWORDS.map((kw) => (
            <button key={kw} onClick={() => { setKeywords(kw); }}
              className="rounded-full bg-sand-100 px-2.5 py-0.5 text-xs text-sand-600 hover:bg-sand-200">
              {kw}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-sand-900">
            Results ({results.length} channels)
          </h2>
          {results.map((r) => (
            <div key={r.channel_id}
              className={`rounded-xl border bg-white p-5 ${r.already_registered ? "border-emerald-200 bg-emerald-50/30" : "border-sand-200"}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-sand-900">{r.channel_name}</h3>
                    {r.already_registered && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        Already registered
                      </span>
                    )}
                  </div>
                  <a href={r.channel_url} target="_blank" rel="noopener noreferrer"
                    className="text-sm text-sea-600 hover:underline block truncate">
                    {r.channel_url}
                  </a>
                  {r.description && (
                    <p className="mt-2 text-sm text-sand-500 line-clamp-2">{r.description}</p>
                  )}
                  <div className="mt-2 flex gap-3 text-xs text-sand-400">
                    {r.subscriber_count && <span>Subscribers: {r.subscriber_count}</span>}
                    {r.video_count && <span>Videos: {r.video_count}</span>}
                  </div>
                </div>

                {!r.already_registered && (
                  <button onClick={() => addChannel(r)}
                    className="shrink-0 rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">
                    Add Channel
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
