"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AgentDetail {
  id: string; name: string; email: string | null; phone: string | null;
  company: string | null; city: string; country: string; is_verified: boolean;
  notes: string | null; created_at: string;
  channels: Array<{ id: string; channel_url: string; channel_name: string | null; status: string; max_videos: number; created_at: string }>;
  properties: Array<{ id: string; title: string | null; property_type: string; price: number | null; neighborhood: string | null; is_published: boolean; created_at: string }>;
  total_properties: number; total_published: number;
}

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [agent, setAgent] = useState<AgentDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [channelUrl, setChannelUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/v1/agents/${id}`);
    if (res.ok) {
      const data = await res.json();
      setAgent(data);
      setForm({ name: data.name, email: data.email || "", phone: data.phone || "", company: data.company || "", city: data.city, country: data.country || "Morocco", notes: data.notes || "" });
    }
    setLoading(false);
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    const res = await fetch(`${API}/api/v1/agents/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) { setMsg("Agent updated"); setEditing(false); load(); }
    else setMsg("Update failed");
  };

  const verify = async () => {
    await fetch(`${API}/api/v1/agents/${id}/verify`, { method: "POST" });
    setMsg("Agent verified"); load();
  };

  const addChannel = async () => {
    if (!channelUrl.trim()) return;
    const res = await fetch(`${API}/api/v1/channels`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_url: channelUrl, agent_id: id, region: "tangier-tetouan" }),
    });
    if (res.ok) { setMsg("Channel added"); setChannelUrl(""); load(); }
    else { const e = await res.json(); setMsg(e.detail || "Failed"); }
  };

  const scanChannel = async (chId: string) => {
    setMsg("Scanning channel...");
    const res = await fetch(`${API}/api/v1/channels/${chId}/scan`, { method: "POST" });
    if (res.ok) { const d = await res.json(); setMsg(`Scan: ${d.submitted} new videos submitted, ${d.skipped_existing} already exist`); }
    else setMsg("Scan failed");
  };

  if (loading) return <div className="mx-auto max-w-5xl py-12 text-center text-sand-400">Loading...</div>;
  if (!agent) return <div className="mx-auto max-w-5xl py-12 text-center text-sand-400">Agent not found</div>;

  const statusColor: Record<string, string> = { pending: "bg-amber-100 text-amber-700", approved: "bg-emerald-100 text-emerald-700", rejected: "bg-red-100 text-red-700", disabled: "bg-sand-200 text-sand-500" };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {/* Breadcrumb */}
      <nav className="mb-6 text-sm text-sand-400">
        <Link href="/admin/agents" className="hover:text-aqar-500">Agents</Link>{" / "}
        <span className="text-sand-700">{agent.name}</span>
      </nav>

      {msg && (
        <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">
          {msg}<button onClick={() => setMsg("")} className="ml-3 text-sea-500 font-bold">x</button>
        </div>
      )}

      {/* ── Agent Header ── */}
      <div className="mb-6 flex items-start justify-between rounded-xl border border-sand-200 bg-white p-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-sand-900">{agent.name}</h1>
            {agent.is_verified
              ? <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">Verified</span>
              : <button onClick={verify} className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700 hover:bg-amber-200">Click to Verify</button>
            }
          </div>
          <div className="mt-2 flex flex-wrap gap-4 text-sm text-sand-500">
            {agent.email && <span>📧 {agent.email}</span>}
            {agent.phone && <span>📞 {agent.phone}</span>}
            {agent.company && <span>🏢 {agent.company}</span>}
            <span>📍 {agent.city}, {agent.country}</span>
            <span>Since {new Date(agent.created_at).toLocaleDateString()}</span>
          </div>
          {agent.notes && <p className="mt-2 text-sm text-sand-400 italic">{agent.notes}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => setEditing(!editing)} className="rounded-lg bg-sand-100 px-4 py-2 text-sm font-medium text-sand-700 hover:bg-sand-200">
            {editing ? "Cancel" : "Edit"}
          </button>
        </div>
      </div>

      {/* ── Edit Form ── */}
      {editing && (
        <div className="mb-6 rounded-xl border border-aqar-200 bg-aqar-50/30 p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            {["name", "email", "phone", "company", "city", "country"].map((f) => (
              <div key={f}>
                <label className="mb-1 block text-xs font-medium text-sand-600 capitalize">{f}</label>
                <input value={form[f] || ""} onChange={(e) => setForm({ ...form, [f]: e.target.value })}
                  className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
              </div>
            ))}
          </div>
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-sand-600">Notes</label>
            <textarea value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={2} className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <button onClick={save} className="mt-3 rounded-lg bg-aqar-500 px-5 py-2 text-sm font-semibold text-white hover:bg-aqar-600">Save</button>
        </div>
      )}

      {/* ── Stats Cards ── */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-sand-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-aqar-600">{agent.channels.length}</p>
          <p className="text-xs text-sand-500">Channels</p>
        </div>
        <div className="rounded-xl border border-sand-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-sea-600">{agent.total_properties}</p>
          <p className="text-xs text-sand-500">Properties</p>
        </div>
        <div className="rounded-xl border border-sand-200 bg-white p-4 text-center">
          <p className="text-2xl font-bold text-emerald-600">{agent.total_published}</p>
          <p className="text-xs text-sand-500">Published</p>
        </div>
      </div>

      {/* ── Channels Section ── */}
      <div className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-sand-900">Channels ({agent.channels.length})</h2>
        </div>

        {/* Add channel form */}
        <div className="mb-3 flex gap-2">
          <input value={channelUrl} onChange={(e) => setChannelUrl(e.target.value)}
            placeholder="https://www.youtube.com/@channel-name"
            className="flex-1 rounded-lg border border-sand-200 px-3 py-2 text-sm focus:border-aqar-400 focus:outline-none" />
          <button onClick={addChannel} className="rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">
            Add Channel
          </button>
        </div>

        {agent.channels.length === 0 ? (
          <p className="rounded-lg bg-sand-50 py-6 text-center text-sm text-sand-400">No channels yet. Add one above or link from Discovery.</p>
        ) : (
          <div className="space-y-2">
            {agent.channels.map((ch) => (
              <div key={ch.id} className="flex items-center justify-between rounded-lg border border-sand-200 bg-white p-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sand-900 text-sm truncate">{ch.channel_name || "Unknown"}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[ch.status] || ""}`}>{ch.status}</span>
                  </div>
                  <a href={ch.channel_url} target="_blank" rel="noopener noreferrer" className="text-xs text-sea-600 hover:underline truncate block">{ch.channel_url}</a>
                </div>
                {ch.status === "approved" && (
                  <button onClick={() => scanChannel(ch.id)} className="shrink-0 rounded-lg bg-sea-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-sea-600">
                    Scan Now
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Properties Section ── */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-sand-900">Properties ({agent.total_properties})</h2>
        {agent.properties.length === 0 ? (
          <p className="rounded-lg bg-sand-50 py-6 text-center text-sm text-sand-400">No properties extracted yet. Scan a channel to start.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-sand-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-sand-100 text-xs text-sand-400">
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Location</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {agent.properties.map((p) => (
                  <tr key={p.id} className="border-b border-sand-50 hover:bg-sand-50">
                    <td className="px-4 py-2.5">
                      <Link href={`/property/${p.id}`} className="text-sea-600 hover:underline text-sm">{p.title || "Untitled"}</Link>
                    </td>
                    <td className="px-4 py-2.5 text-sand-600 capitalize">{p.property_type}</td>
                    <td className="px-4 py-2.5 font-medium text-aqar-600">{p.price ? `${p.price.toLocaleString()} MAD` : "-"}</td>
                    <td className="px-4 py-2.5 text-sand-500">{p.neighborhood || "-"}</td>
                    <td className="px-4 py-2.5">
                      {p.is_published
                        ? <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">Published</span>
                        : <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">Draft</span>
                      }
                    </td>
                    <td className="px-4 py-2.5 text-xs text-sand-400">{new Date(p.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
