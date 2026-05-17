"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AgentItem { id: string; name: string; email: string | null; phone: string | null; company: string | null; city: string; country: string; is_verified: boolean; channels_count: number; properties_count: number; created_at: string; }

export default function AdminAgentsPage() {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "", city: "Tangier", country: "Morocco" });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => { setLoading(true); const r = await fetch(`${API}/api/v1/agents`); if (r.ok) setAgents(await r.json()); setLoading(false); }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!form.name.trim()) return;
    const r = await fetch(`${API}/api/v1/agents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
    if (r.ok) { setMsg("Agent created"); setShowCreate(false); setForm({ name: "", email: "", phone: "", company: "", city: "Tangier", country: "Morocco" }); load(); }
    else { const e = await r.json(); setMsg(e.detail || "Failed"); }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sand-900">Agents ({agents.length})</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">{showCreate ? "Cancel" : "New Agent"}</button>
      </div>

      {msg && <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">{msg}<button onClick={() => setMsg("")} className="ml-2">x</button></div>}

      {showCreate && (
        <div className="mb-6 rounded-xl border border-aqar-200 bg-aqar-50 p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            {Object.entries(form).map(([k, v]) => (
              <div key={k}><label className="mb-1 block text-xs font-medium text-sand-600 capitalize">{k}</label>
              <input value={v} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" /></div>
            ))}
          </div>
          <button onClick={create} className="mt-3 rounded-lg bg-aqar-500 px-5 py-2 text-sm font-semibold text-white hover:bg-aqar-600">Create</button>
        </div>
      )}

      {loading ? <div className="py-12 text-center text-sand-400">Loading...</div> :
      agents.length === 0 ? <div className="rounded-xl border border-sand-200 bg-white py-12 text-center text-sand-400">No agents yet</div> :
      <div className="space-y-2">
        {agents.map((a) => (
          <Link key={a.id} href={`/admin/agents/${a.id}`} className="flex items-center justify-between rounded-xl border border-sand-200 bg-white p-4 hover:border-aqar-300 hover:shadow transition-all">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sand-900">{a.name}</span>
                {a.is_verified ? <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">Verified</span> : <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">Pending</span>}
              </div>
              <div className="mt-1 flex gap-3 text-xs text-sand-500">
                {a.email && <span>{a.email}</span>}
                {a.company && <span>{a.company}</span>}
                <span>{a.city}, {a.country}</span>
              </div>
            </div>
            <div className="flex gap-4 text-center">
              <div><p className="text-lg font-bold text-sea-600">{a.channels_count}</p><p className="text-xs text-sand-400">Channels</p></div>
              <div><p className="text-lg font-bold text-aqar-600">{a.properties_count}</p><p className="text-xs text-sand-400">Properties</p></div>
            </div>
          </Link>
        ))}
      </div>}
    </div>
  );
}
