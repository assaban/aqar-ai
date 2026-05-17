"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Channel { id: string; channel_url: string; channel_name: string | null; channel_id: string | null; description: string | null; region: string; status: string; max_videos: number; discovered_via: string | null; rejection_reason: string | null; agent_id: string | null; agent_name: string | null; tags: any; created_at: string; approved_at: string | null; }

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = filter === "all" ? `${API}/api/v1/channels` : `${API}/api/v1/channels?status=${filter}`;
    const r = await fetch(url);
    if (r.ok) setChannels(await r.json());
    setLoading(false);
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  const action = async (path: string, body?: any) => {
    const r = await fetch(`${API}${path}`, { method: "POST", headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    if (r.ok) { const d = await r.json(); setMsg(JSON.stringify(d).substring(0, 120)); load(); }
    else setMsg("Action failed");
  };

  const approve = (id: string) => action(`/api/v1/channels/${id}/approve`, { status: "approved" });
  const reject = (id: string) => { const reason = prompt("Reason?"); if (reason) action(`/api/v1/channels/${id}/approve`, { status: "rejected", rejection_reason: reason }); };
  const disable = (id: string) => action(`/api/v1/channels/${id}/disable`);
  const scan = (id: string) => { setMsg("Scanning..."); action(`/api/v1/channels/${id}/scan`); };

  const sc: Record<string, string> = { pending: "bg-amber-100 text-amber-700", approved: "bg-emerald-100 text-emerald-700", rejected: "bg-red-100 text-red-700", disabled: "bg-sand-200 text-sand-500" };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sand-900">Channels ({channels.length})</h1>
        <Link href="/admin/discover" className="rounded-lg bg-sea-500 px-4 py-2 text-sm font-medium text-white hover:bg-sea-600">Discover</Link>
      </div>

      {msg && <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">{msg}<button onClick={() => setMsg("")} className="ml-2 font-bold">x</button></div>}

      <div className="mb-4 flex gap-2">
        {["all", "pending", "approved", "rejected", "disabled"].map((s) => (
          <button key={s} onClick={() => setFilter(s)} className={`rounded-lg px-3 py-1.5 text-sm capitalize ${filter === s ? "bg-aqar-500 text-white" : "bg-sand-100 text-sand-600 hover:bg-sand-200"}`}>{s}</button>
        ))}
      </div>

      {loading ? <div className="py-12 text-center text-sand-400">Loading...</div> :
      channels.length === 0 ? <div className="rounded-xl border border-sand-200 bg-white py-12 text-center text-sand-400">No channels. <Link href="/admin/discover" className="text-aqar-500 underline">Discover some</Link></div> :
      <div className="space-y-2">
        {channels.map((ch) => (
          <div key={ch.id} className="rounded-xl border border-sand-200 bg-white p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-semibold text-sand-900 truncate">{ch.channel_name || "Unknown"}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${sc[ch.status] || ""}`}>{ch.status}</span>
                </div>
                <a href={ch.channel_url} target="_blank" rel="noopener noreferrer" className="text-xs text-sea-600 hover:underline truncate block">{ch.channel_url}</a>
                <div className="mt-1 flex flex-wrap gap-3 text-xs text-sand-400">
                  <span>Region: {ch.region}</span>
                  <span>Max: {ch.max_videos}</span>
                  {ch.agent_name && <span>Agent: <Link href={`/admin/agents`} className="text-sea-600">{ch.agent_name}</Link></span>}
                  {ch.discovered_via && <span>Via: {ch.discovered_via}</span>}
                </div>
                {ch.rejection_reason && <p className="mt-1 text-xs text-red-500">Reason: {ch.rejection_reason}</p>}
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                {ch.status === "pending" && (<>
                  <button onClick={() => approve(ch.id)} className="rounded bg-emerald-500 px-3 py-1 text-xs text-white hover:bg-emerald-600">Approve</button>
                  <button onClick={() => reject(ch.id)} className="rounded bg-red-500 px-3 py-1 text-xs text-white hover:bg-red-600">Reject</button>
                </>)}
                {ch.status === "approved" && (<>
                  <button onClick={() => scan(ch.id)} className="rounded bg-sea-500 px-3 py-1 text-xs text-white hover:bg-sea-600">Scan Now</button>
                  <button onClick={() => disable(ch.id)} className="rounded bg-sand-300 px-3 py-1 text-xs text-sand-700">Disable</button>
                </>)}
              </div>
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}
