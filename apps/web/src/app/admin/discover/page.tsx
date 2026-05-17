"use client";
import {useEffect, useState} from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Discovered {
    channel_id: string;
    channel_name: string;
    channel_url: string;
    description: string;
    video_count: number | null;
    recent_upload: string | null;
    recent_upload_date: string | null;
    already_registered: boolean;
    existing_channel_id: string | null;
}

interface AgentOption {
    id: string;
    name: string;
}

const KEYWORDS = ["عقارات طنجة", "عقارات تطوان", "شقق للبيع طنجة", "شقق للبيع تطوان", "immobilier tanger", "immobilier tetouan", "real estate tetouan morocco", "real estate tangier morocco", "بيع شراء طنجة تطوان", "villa tanger", "terrain tanger", "villa tetouan", "terrain tetouan"];

export default function DiscoverPage() {
    const [keywords, setKeywords] = useState("");
    const [maxResults, setMaxResults] = useState(15);
    const [results, setResults] = useState<Discovered[]>([]);
    const [agents, setAgents] = useState<AgentOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState("");

    useEffect(() => {
        fetch(`${API}/api/v1/agents`).then(r => r.json()).then((data: any[]) =>
            setAgents(data.map(a => ({id: a.id, name: a.name})))
        ).catch(() => {
        });
    }, []);

    const search = async () => {
        if (!keywords.trim()) return;
        setLoading(true);
        setMsg("");
        const r = await fetch(`${API}/api/v1/channels/discover`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({keywords, max_results: maxResults})
        });
        if (r.ok) {
            const d = await r.json();
            setResults(d);
            setMsg(`Found ${d.length} channels`);
        } else setMsg("Search failed");
        setLoading(false);
    };

    const addChannel = async (ch: Discovered, agentId?: string) => {
        const r = await fetch(`${API}/api/v1/channels`, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                channel_url: ch.channel_url,
                channel_name: ch.channel_name,
                description: ch.description,
                region: "tangier-tetouan",
                agent_id: agentId || null
            })
        });
        if (r.ok) {
            setMsg(`Added: ${ch.channel_name}`);
            setResults(results.map(c => c.channel_id === ch.channel_id ? {...c, already_registered: true} : c));
        } else {
            const e = await r.json();
            setMsg(e.detail || "Failed");
        }
    };

    const linkToAgent = async (existingChannelId: string, agentId: string) => {
        const r = await fetch(`${API}/api/v1/channels/${existingChannelId}/link`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({agent_id: agentId})
        });
        if (r.ok) setMsg("Channel linked to agent");
        else setMsg("Linking failed");
    };

    return (
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
            <h1 className="mb-2 text-2xl font-bold text-sand-900">Discover YouTube Channels</h1>
            <p className="mb-6 text-sm text-sand-500">Search YouTube for real estate channels. Channels with recent
                uploads and high activity appear first.</p>

            {msg &&
                <div className="mb-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">{msg}
                    <button onClick={() => setMsg("")} className="ml-2">x</button>
                </div>}

            <div className="mb-6 rounded-xl border border-sand-200 bg-white p-5">
                <div className="flex gap-3 mb-3">
                    <input value={keywords} onChange={(e) => setKeywords(e.target.value)}
                           placeholder="Search keywords..."
                           className="flex-1 rounded-lg border border-sand-200 px-4 py-2.5 text-sm"
                           onKeyDown={(e) => e.key === "Enter" && search()}/>
                    <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))}
                            className="rounded-lg border border-sand-200 px-3 py-2.5 text-sm">
                        <option value={10}>10</option>
                        <option value={15}>15</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                    </select>
                    <button onClick={search} disabled={loading}
                            className="rounded-lg bg-sea-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-sea-600 disabled:opacity-50">{loading ? "Searching..." : "Search"}</button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                    {KEYWORDS.map((kw) => <button key={kw} onClick={() => setKeywords(kw)}
                                                  className="rounded-full bg-sand-100 px-2.5 py-0.5 text-xs text-sand-600 hover:bg-sand-200">{kw}</button>)}
                </div>
            </div>

            {results.length > 0 && (
                <div className="space-y-3">
                    {results.map((ch) => (
                        <div key={ch.channel_id}
                             className={`rounded-xl border bg-white p-5 ${ch.already_registered ? "border-emerald-200" : "border-sand-200"}`}>
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h3 className="font-semibold text-sand-900">{ch.channel_name}</h3>
                                        {ch.already_registered && (
                                            <Link
                                                href={`/admin/channels`} // Anchors directly onto backoffice records
                                                className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700 hover:underline"
                                            >
                                                Already Registered (View Ledger)
                                            </Link>
                                        )}
                                    </div>
                                    <a href={ch.channel_url} target="_blank" rel="noopener noreferrer"
                                       className="text-sm text-sea-600 hover:underline block truncate">{ch.channel_url}</a>
                                    {ch.description &&
                                        <p className="mt-1 text-sm text-sand-500 line-clamp-2">{ch.description}</p>}
                                    {ch.recent_upload && (
                                        <p className="mt-1 text-xs text-sand-400">Latest:
                                            "{ch.recent_upload}" {ch.recent_upload_date && `(${ch.recent_upload_date.substring(0, 4)}-${ch.recent_upload_date.substring(4, 6)}-${ch.recent_upload_date.substring(6, 8)})`}</p>
                                    )}
                                </div>

                                <div className="shrink-0 flex flex-col gap-1.5 items-end">
                                    {!ch.already_registered ? (
                                        <>
                                            <button onClick={() => addChannel(ch)}
                                                    className="rounded-lg bg-aqar-500 px-4 py-1.5 text-xs font-medium text-white hover:bg-aqar-600">Add
                                                Channel
                                            </button>
                                            {agents.length > 0 && (
                                                <select onChange={(e) => {
                                                    if (e.target.value) addChannel(ch, e.target.value);
                                                    e.target.value = "";
                                                }}
                                                        className="rounded-lg border border-sand-200 px-2 py-1 text-xs text-sand-600"
                                                        defaultValue="">
                                                    <option value="" disabled>Add & link to agent...</option>
                                                    {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                                                </select>
                                            )}
                                        </>
                                    ) : (
                                        ch.existing_channel_id && agents.length > 0 && (
                                            <select onChange={(e) => {
                                                if (e.target.value && ch.existing_channel_id) linkToAgent(ch.existing_channel_id, e.target.value);
                                                e.target.value = "";
                                            }}
                                                    className="rounded-lg border border-sand-200 px-2 py-1 text-xs text-sand-600"
                                                    defaultValue="">
                                                <option value="" disabled>Link to agent...</option>
                                                {agents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                                            </select>
                                        )
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
