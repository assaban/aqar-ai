"use client";

import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Step = "register" | "channel" | "done";

export default function AgentRegisterPage() {
  const [step, setStep] = useState<Step>("register");
  const [agentId, setAgentId] = useState("");
  const [msg, setMsg] = useState("");

  const [agent, setAgent] = useState({ name: "", email: "", phone: "", company: "", city: "Tangier" });
  const [channel, setChannel] = useState({ channel_url: "", channel_name: "", description: "" });

  const registerAgent = async () => {
    if (!agent.name.trim()) { setMsg("Name is required"); return; }
    const res = await fetch(`${API}/api/v1/agents`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(agent),
    });
    if (res.ok) {
      const data = await res.json();
      setAgentId(data.id);
      setStep("channel");
      setMsg("");
    } else {
      const err = await res.json();
      setMsg(err.detail || "Registration failed");
    }
  };

  const addChannel = async () => {
    if (!channel.channel_url.trim()) { setMsg("Channel URL is required"); return; }
    const res = await fetch(`${API}/api/v1/channels`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...channel, agent_id: agentId, region: "tangier-tetouan" }),
    });
    if (res.ok) {
      setStep("done");
      setMsg("");
    } else {
      const err = await res.json();
      setMsg(err.detail || "Failed to add channel");
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 text-4xl">🏠</div>
        <h1 className="text-2xl font-bold text-sand-900">List Your Properties on Aqar.ai</h1>
        <p className="mt-2 text-sand-500">
          Register as an agent and connect your YouTube channel. Our AI will automatically
          extract property data from your video tours and list them on our portal.
        </p>
      </div>

      {/* Progress steps */}
      <div className="mb-8 flex justify-center gap-4 text-sm">
        {[
          { key: "register", label: "1. Your Info" },
          { key: "channel", label: "2. Your Channel" },
          { key: "done", label: "3. Done" },
        ].map((s) => (
          <div key={s.key} className={`flex items-center gap-1.5 ${step === s.key ? "text-aqar-600 font-semibold" : step === "done" || (step === "channel" && s.key === "register") ? "text-emerald-500" : "text-sand-400"}`}>
            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${step === s.key ? "bg-aqar-500 text-white" : step === "done" || (step === "channel" && s.key === "register") ? "bg-emerald-100 text-emerald-600" : "bg-sand-200 text-sand-500"}`}>
              {(step === "done" || (step === "channel" && s.key === "register")) ? "✓" : s.label[0]}
            </span>
            {s.label.substring(3)}
          </div>
        ))}
      </div>

      {msg && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
          {msg}
        </div>
      )}

      {/* Step 1: Agent info */}
      {step === "register" && (
        <div className="rounded-xl border border-sand-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-sand-900">Your Information</h2>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-sand-700">Full Name *</label>
              <input value={agent.name} onChange={(e) => setAgent({ ...agent, name: e.target.value })}
                className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                placeholder="e.g. Ahmed Benali" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-sand-700">Email</label>
                <input type="email" value={agent.email} onChange={(e) => setAgent({ ...agent, email: e.target.value })}
                  className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                  placeholder="ahmed@example.com" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-sand-700">Phone</label>
                <input value={agent.phone} onChange={(e) => setAgent({ ...agent, phone: e.target.value })}
                  className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                  placeholder="+212 6XX XXX XXX" />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-sand-700">Agency / Company</label>
                <input value={agent.company} onChange={(e) => setAgent({ ...agent, company: e.target.value })}
                  className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                  placeholder="e.g. Tangier Immo" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-sand-700">City</label>
                <input value={agent.city} onChange={(e) => setAgent({ ...agent, city: e.target.value })}
                  className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400" />
              </div>
            </div>
          </div>
          <button onClick={registerAgent}
            className="mt-5 w-full rounded-lg bg-aqar-500 py-3 font-semibold text-white hover:bg-aqar-600 transition-colors">
            Continue
          </button>
        </div>
      )}

      {/* Step 2: Channel */}
      {step === "channel" && (
        <div className="rounded-xl border border-sand-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-sand-900">Connect Your YouTube Channel</h2>
          <p className="mb-4 text-sm text-sand-500">
            Add your YouTube channel URL. Our system will automatically scan your videos,
            transcribe the Arabic/Darija content, and extract property details.
          </p>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-sand-700">YouTube Channel URL *</label>
              <input value={channel.channel_url} onChange={(e) => setChannel({ ...channel, channel_url: e.target.value })}
                className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                placeholder="https://www.youtube.com/@your-channel" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-sand-700">Channel Name</label>
              <input value={channel.channel_name} onChange={(e) => setChannel({ ...channel, channel_name: e.target.value })}
                className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                placeholder="Your channel display name" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-sand-700">Description</label>
              <textarea value={channel.description} onChange={(e) => setChannel({ ...channel, description: e.target.value })}
                rows={3} className="w-full rounded-lg border border-sand-200 px-4 py-2.5 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
                placeholder="Tell us about your channel and property types..." />
            </div>
          </div>
          <div className="mt-5 flex gap-3">
            <button onClick={addChannel}
              className="flex-1 rounded-lg bg-aqar-500 py-3 font-semibold text-white hover:bg-aqar-600 transition-colors">
              Submit Channel
            </button>
            <button onClick={() => setStep("done")}
              className="rounded-lg bg-sand-200 px-6 py-3 font-medium text-sand-700 hover:bg-sand-300">
              Skip for Now
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Done */}
      {step === "done" && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center">
          <div className="mb-3 text-4xl">🎉</div>
          <h2 className="text-xl font-bold text-sand-900">Registration Complete!</h2>
          <p className="mt-2 text-sand-600">
            Thank you for registering. Your channel will be reviewed by our team and
            approved shortly. Once approved, your videos will be automatically processed.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link href="/agent/submit"
              className="rounded-lg bg-aqar-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-aqar-600">
              Submit a Video Directly
            </Link>
            <Link href="/"
              className="rounded-lg bg-sand-200 px-5 py-2.5 text-sm font-medium text-sand-700 hover:bg-sand-300">
              Go to Home
            </Link>
          </div>
        </div>
      )}

      {/* Benefits section */}
      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        {[
          { icon: "🤖", title: "Automatic Extraction", desc: "AI extracts price, area, rooms, and location from your video tours." },
          { icon: "🗺️", title: "Map Visibility", desc: "Properties are geocoded and shown on an interactive map for seekers." },
          { icon: "📊", title: "Analytics", desc: "Track how your properties perform with detailed view statistics." },
        ].map((b) => (
          <div key={b.title} className="rounded-xl border border-sand-200 bg-white p-4 text-center">
            <div className="mb-2 text-2xl">{b.icon}</div>
            <h3 className="mb-1 text-sm font-semibold text-sand-900">{b.title}</h3>
            <p className="text-xs text-sand-500">{b.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
