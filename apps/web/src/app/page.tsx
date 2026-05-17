import Link from "next/link";
import { fetchStats } from "@/lib/api"; // Uses your unified client
import { RecentProperties } from "@/components/RecentProperties";

export default async function HomePage() {
  // Fetch stats server-side (uses http://api:8000 internally)
  const stats = await fetchStats().catch(() => null);

  return (
    <div className="bg-sand-50">
      {/* ── Hero Section ── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-aqar-600 via-aqar-500 to-aqar-400 pb-24 pt-20 text-white">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTTAgMCBMNjAgNjAgTTYwIDAgTDAgNjAiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuMDUiIHN0cm9rZS13aWR0aD0iMSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3QgZmlsbD0idXJsKCNnKSIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIvPjwvc3ZnPg==')] opacity-50" />

        <div className="relative mx-auto max-w-5xl px-4 text-center sm:px-6">
          <h1 className="mb-6 text-5xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
            Real Estate <span className="text-aqar-100">AI-Powered</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-aqar-100/90 sm:text-xl">
            Automatically extracting structured property data from Moroccan social media tours.
            We turn spoken Darija and Arabic into searchable listings.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/search" className="rounded-xl bg-white px-8 py-4 text-lg font-bold text-aqar-600 shadow-xl transition-all hover:bg-sand-50 hover:scale-105">
              Explore Properties
            </Link>
            <Link href="/agents" className="rounded-xl border-2 border-white/30 px-8 py-4 text-lg font-bold text-white transition-all hover:bg-white/10">
              Partners Portal
            </Link>
          </div>
        </div>
      </section>

      {/* ── Real-Time Stats (From API) ── */}
      <section className="relative z-10 -mt-12 mx-auto max-w-5xl px-4">
        <div className="grid grid-cols-2 gap-4 rounded-3xl border border-sand-200 bg-white p-8 shadow-2xl sm:grid-cols-4">
          <StatItem label="Properties Found" value={stats?.total_properties ?? "..."} />
          <StatItem label="Videos Scanned" value={stats?.total_videos ?? "..."} />
          <StatItem label="Regions Active" value={1} />
          <StatItem label="AI Accuracy" value={`${((stats?.avg_extraction_confidence ?? 0.85) * 100).toFixed(0)}%`} />
        </div>
      </section>

      {/* ── Recent Properties (Horizontal Scroll) ── */}
      <RecentProperties />

      {/* ── Features Section ── */}
      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
        <h2 className="mb-16 text-center text-3xl font-bold text-sand-900 sm:text-4xl">The Future of Moroccan Property Search</h2>
        <div className="grid gap-12 sm:grid-cols-3">
          <FeatureCard
            icon="🎙️"
            title="Transcription"
            desc="Our system listens to YouTube tours, transcribing Darija dialects into clean property metadata."
          />
          <FeatureCard
            icon="🧠"
            title="LLM Extraction"
            desc="Advanced AI identifies prices, square footage, and room counts from unstructured speech."
          />
          <FeatureCard
            icon="📍"
            title="Geo-Mapping"
            desc="Automatic neighborhood detection places listings precisely on the Tangier-Tetouan map."
          />
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-sand-200 bg-white py-12">
        <div className="mx-auto max-w-6xl px-4 text-center text-sand-400">
          <p className="font-bold text-sand-600 uppercase tracking-widest text-xs mb-2">Aqar.ai Pipeline</p>
          <p className="text-sm">Master Thesis Project • Computer Science • Morocco</p>
        </div>
      </footer>
    </div>
  );
}

// ── Components ──────────────────────────────────────────────────

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <p className="text-3xl font-black text-aqar-600">{value}</p>
      <p className="text-[10px] font-bold uppercase tracking-widest text-sand-400 mt-1">{label}</p>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="rounded-3xl border border-sand-100 bg-white p-8 transition-shadow hover:shadow-lg">
      <div className="mb-6 text-5xl">{icon}</div>
      <h3 className="mb-3 text-xl font-bold text-sand-900">{title}</h3>
      <p className="text-sand-500 leading-relaxed">{desc}</p>
    </div>
  );
}