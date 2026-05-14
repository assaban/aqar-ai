"use client";

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Agent {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  city: string;
  is_verified: boolean;
  channels_count: number;
  created_at: string;
}

export default function AdminAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "", city: "Tangier" });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`${API}/api/v1/agents`);
    if (res.ok) setAgents(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const verify = async (id: string) => {
    await fetch(`${API}/api/v1/agents/${id}/verify`, { method: "POST" });
    setMsg("Agent verified"); load();
  };

  const create = async () => {
    if (!form.name.trim()) return;
    const res = await fetch(`${API}/api/v1/agents`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setMsg("Agent created"); setShowCreate(false);
      setForm({ name: "", email: "", phone: "", company: "", city: "Tangier" });
      load();
    } else {
      const err = await res.json();
      setMsg(`Error: ${err.detail || "Failed"}`);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sand-900">Agent Management</h1>
        <button onClick={() => setShowCreate(!showCreate)}
          className="rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">
          {showCreate ? "Cancel" : "Add Agent"}
        </button>
      </div>

      {msg && (
        <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">
          {msg}<button onClick={() => setMsg("")} className="ml-2 text-sea-500">x</button>
        </div>
      )}

      {/* Create agent form */}
      {showCreate && (
        <div className="mb-6 rounded-xl border border-aqar-200 bg-aqar-50 p-5">
          <h3 className="mb-3 font-semibold text-sand-900">New Agent</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Full name *" className="rounded-lg border border-sand-200 px-3 py-2 text-sm" />
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="Email" type="email" className="rounded-lg border border-sand-200 px-3 py-2 text-sm" />
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="Phone" className="rounded-lg border border-sand-200 px-3 py-2 text-sm" />
            <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })}
              placeholder="Company/Agency" className="rounded-lg border border-sand-200 px-3 py-2 text-sm" />
            <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}
              placeholder="City" className="rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <button onClick={create} className="mt-3 rounded-lg bg-aqar-500 px-4 py-2 text-sm font-medium text-white hover:bg-aqar-600">
            Create Agent
          </button>
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sand-400">Loading agents...</div>
      ) : agents.length === 0 ? (
        <div className="rounded-xl border border-sand-200 bg-white py-12 text-center text-sand-400">
          No agents registered yet.
        </div>
      ) : (
        <div className="space-y-3">
          {agents.map((a) => (
            <div key={a.id} className="rounded-xl border border-sand-200 bg-white p-5 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-sand-900">{a.name}</h3>
                  {a.is_verified ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">Verified</span>
                  ) : (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Unverified</span>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap gap-3 text-xs text-sand-500">
                  {a.email && <span>{a.email}</span>}
                  {a.phone && <span>{a.phone}</span>}
                  {a.company && <span>{a.company}</span>}
                  <span>{a.city}</span>
                  <span>{a.channels_count} channel(s)</span>
                  <span>Joined: {new Date(a.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex gap-2">
                {!a.is_verified && (
                  <button onClick={() => verify(a.id)}
                    className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-600">
                    Verify
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
