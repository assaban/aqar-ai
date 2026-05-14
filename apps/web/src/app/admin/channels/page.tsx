"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Channel {
  id: string;
  channel_url: string;
  channel_name: string | null;
  description: string | null;
  region: string;
  status: string;
  max_videos: number;
  discovered_via: string | null;
  rejection_reason: string | null;
  agent_name: string | null;
  created_at: string;
  approved_at: string | null;
}

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const url = filter === "all" ? `${API}/api/v1/channels` : `${API}/api/v1/channels?status=${filter}`;
    const res = await fetch(url);
    if (res.ok) setChannels(await res.json());
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const approve = async (id: string) => {
    const res = await fetch(`${API}/api/v1/channels/${id}/approve`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "approved" }),
    });
    if (res.ok) { setActionMsg("Channel approved"); load(); }
  };

  const reject = async (id: string) => {
    const reason = prompt("Rejection reason:");
    if (!reason) return;
    const res = await fetch(`${API}/api/v1/channels/${id}/approve`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "rejected", rejection_reason: reason }),
    });
    if (res.ok) { setActionMsg("Channel rejected"); load(); }
  };

  const disable = async (id: string) => {
    const res = await fetch(`${API}/api/v1/channels/${id}/disable`, { method: "POST" });
    if (res.ok) { setActionMsg("Channel disabled"); load(); }
  };

  const triggerScan = async (channelUrl: string) => {
    setActionMsg(`Triggering scan for ${channelUrl}...`);
    const res = await fetch(`${API}/api/v1/pipeline/submit`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: channelUrl }),
    });
    setActionMsg(res.ok ? "Scan triggered! Check pipeline status." : "Scan failed. The channel URL must be a video URL for now.");
  };

  const statusColor: Record<string, string> = {
    pending: "bg-amber-100 text-amber-700",
    approved: "bg-emerald-100 text-emerald-700",
    rejected: "bg-red-100 text-red-700",
    disabled: "bg-sand-200 text-sand-500",
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sand-900">Channel Management</h1>
        <Link href="/admin/discover" className="rounded-lg bg-sea-500 px-4 py-2 text-sm font-medium text-white hover:bg-sea-600">
          Discover Channels
        </Link>
      </div>

      {actionMsg && (
        <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">
          {actionMsg}
          <button onClick={() => setActionMsg("")} className="ml-2 text-sea-500">x</button>
        </div>
      )}

      {/* Filter tabs */}
      <div className="mb-4 flex gap-2">
        {["all", "pending", "approved", "rejected", "disabled"].map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`rounded-lg px-3 py-1.5 text-sm capitalize ${filter === s ? "bg-aqar-500 text-white" : "bg-sand-100 text-sand-600 hover:bg-sand-200"}`}>
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 text-center text-sand-400">Loading channels...</div>
      ) : channels.length === 0 ? (
        <div className="rounded-xl border border-sand-200 bg-white py-12 text-center text-sand-400">
          No channels found. <Link href="/admin/discover" className="text-aqar-500 underline">Discover some</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {channels.map((ch) => (
            <div key={ch.id} className="rounded-xl border border-sand-200 bg-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-sand-900 truncate">{ch.channel_name || "Unknown Channel"}</h3>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[ch.status] || ""}`}>
                      {ch.status}
                    </span>
                  </div>
                  <a href={ch.channel_url} target="_blank" rel="noopener noreferrer" className="text-sm text-sea-600 hover:underline truncate block">
                    {ch.channel_url}
                  </a>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-sand-500">
                    <span>Region: {ch.region}</span>
                    <span>Max videos: {ch.max_videos}</span>
                    {ch.agent_name && <span>Agent: {ch.agent_name}</span>}
                    {ch.discovered_via && <span>Source: {ch.discovered_via}</span>}
                    <span>Added: {new Date(ch.created_at).toLocaleDateString()}</span>
                  </div>
                  {ch.description && <p className="mt-2 text-sm text-sand-500 line-clamp-2">{ch.description}</p>}
                  {ch.rejection_reason && <p className="mt-1 text-sm text-red-500">Rejected: {ch.rejection_reason}</p>}
                </div>

                <div className="flex flex-col gap-1.5 shrink-0">
                  {ch.status === "pending" && (
                    <>
                      <button onClick={() => approve(ch.id)} className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-600">Approve</button>
                      <button onClick={() => reject(ch.id)} className="rounded-lg bg-red-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600">Reject</button>
                    </>
                  )}
                  {ch.status === "approved" && (
                    <>
                      <button onClick={() => triggerScan(ch.channel_url)} className="rounded-lg bg-aqar-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-aqar-600">Scan Now</button>
                      <button onClick={() => disable(ch.id)} className="rounded-lg bg-sand-300 px-3 py-1.5 text-xs font-medium text-sand-700 hover:bg-sand-400">Disable</button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
