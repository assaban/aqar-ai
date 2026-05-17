"use client";
import { useEffect, useState, use } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BrowseVideo {
  external_id: string;
  title: string;
  url: string;
  duration_seconds: number;
  published_at: string | null;
  already_listed: boolean;
}

export default function ChannelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [channel, setChannel] = useState<any>(null);
  const [videos, setVideos] = useState<BrowseVideo[]>([]);
  const [showMore, setShowMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    async function getChannelData() {
      const cRes = await fetch(`${API}/api/v1/channels`);
      if (cRes.ok) {
        const list = await cRes.json();
        const found = list.find((item: any) => item.id === id);
        setChannel(found);

        if (found) {
          const vRes = await fetch(`${API}/api/v1/channels/${found.id}/browse-videos`);
          if (vRes.ok) setVideos(await vRes.json());
        }
      }
      setLoading(false);
    }
    getChannelData();
  }, [id]);

  const scanIndividualVideo = async (url: string) => {
    setMsg("Submitting single video to pipeline...");
    const res = await fetch(`${API}/api/v1/pipeline/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    setMsg(res.ok ? "Video submitted successfully!" : "Pipeline insertion failed.");
  };

  if (loading) return <div className="p-12 text-center text-sand-400">Loading profile workspace...</div>;
  if (!channel) return <div className="p-12 text-center text-red-500">Channel not found.</div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <Link href="/admin/channels" className="text-sm text-sand-400 hover:text-aqar-500">← Back to Tracking Ledger</Link>

      {/* YouTube Page Header Component Simulation */}
      <div className="mt-6 border-b border-sand-200 bg-white p-6 rounded-2xl shadow-sm">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-tr from-aqar-500 to-amber-500 text-white font-bold text-3xl shadow-md">
            {channel.channel_name ? channel.channel_name[0] : "ع"}
          </div>
          <div className="flex-1 text-center md:text-left">
            <h1 className="text-2xl font-black text-sand-900">{channel.channel_name || "Unverified Agency"}</h1>
            <p className="text-sm text-sand-400 mt-1">@{channel.channel_id || "youtube_handle"} • Max Videos: {channel.max_videos}</p>

            <div className="mt-3 max-w-2xl text-sm text-sand-600">
              <p className={showMore ? "" : "line-clamp-2"}>{channel.description || "No localized biography provided."}</p>
              <button onClick={() => setShowMore(!showMore)} className="mt-1 font-bold text-aqar-500 hover:text-aqar-600 text-xs uppercase">
                {showMore ? "Show Less ▴" : "More Details ▾"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {msg && <div className="mt-4 rounded-lg bg-sea-50 border border-sea-200 px-4 py-2 text-sm text-sea-700">{msg}</div>}

      {/* Selective List Feed */}
      <h2 className="mt-8 mb-4 text-lg font-bold text-sand-900">Select Videos to Feature</h2>
      <div className="grid gap-3">
        {videos.map((v) => (
          <div key={v.external_id} className="flex items-center justify-between rounded-xl border border-sand-200 bg-white p-4">
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-sand-900 text-sm truncate">{v.title}</p>
              <p className="text-xs text-sand-400 mt-0.5">
                Duration: {Math.round(v.duration_seconds / 60)}m | Published: {v.published_at ? new Date(v.published_at).toLocaleDateString() : "N/A"}
              </p>
            </div>
            <button
              onClick={() => scanIndividualVideo(v.url)}
              disabled={v.already_listed}
              className={`ml-4 rounded-lg px-4 py-1.5 text-xs font-bold transition-all ${v.already_listed ? "bg-sand-100 text-sand-400 cursor-not-allowed" : "bg-aqar-500 text-white hover:bg-aqar-600"}`}
            >
              {v.already_listed ? "Indexed" : "Parse & List"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}