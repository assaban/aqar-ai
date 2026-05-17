import { formatPrice } from "@/lib/utils";
import { serverFetch } from "@/lib/server-api";

async function getStats() {
  return serverFetch<Record<string, any>>("/api/v1/stats", { revalidate: 60 });
}

async function getNeighborhoodStats() {
  return serverFetch<Record<string, any>>("/api/v1/stats/neighborhoods", { revalidate: 60 });
}

export default async function StatsPage() {
  const [stats, neighborhoods] = await Promise.all([getStats(), getNeighborhoodStats()]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="mb-8 text-2xl font-bold text-sand-900">Dashboard</h1>

      {/* Summary cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Videos Processed" value={stats?.total_videos ?? 0} icon="📹" />
        <StatCard label="Properties Extracted" value={stats?.total_properties ?? 0} icon="🏠" />
        <StatCard label="Published" value={stats?.total_published ?? 0} icon="✅" />
        <StatCard
          label="Avg Confidence"
          value={stats?.avg_extraction_confidence ? `${Math.round(stats.avg_extraction_confidence * 100)}%` : "N/A"}
          icon="🎯"
        />
      </div>

      {/* Pipeline status */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <StatCard label="Pending" value={stats?.processing_pending ?? 0} icon="⏳" />
        <StatCard label="Completed" value={stats?.processing_completed ?? 0} icon="✅" />
        <StatCard label="Failed" value={stats?.processing_failed ?? 0} icon="❌" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Property type breakdown */}
        {stats?.property_types && Object.keys(stats.property_types).length > 0 && (
          <div className="rounded-xl border border-sand-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-sand-900">Property Types</h2>
            <div className="space-y-3">
              {Object.entries(stats.property_types)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([type, count]) => (
                  <BarItem key={type} label={type} value={count as number} total={stats.total_properties} />
                ))}
            </div>
          </div>
        )}

        {/* Listing type breakdown */}
        {stats?.listing_types && Object.keys(stats.listing_types).length > 0 && (
          <div className="rounded-xl border border-sand-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-sand-900">Listing Types</h2>
            <div className="space-y-3">
              {Object.entries(stats.listing_types)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([type, count]) => (
                  <BarItem key={type} label={type} value={count as number} total={stats.total_properties} />
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Neighborhood stats */}
      {neighborhoods?.neighborhoods?.length > 0 && (
        <div className="mt-6 rounded-xl border border-sand-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-sand-900">
            Neighborhood Statistics ({neighborhoods.total_neighborhoods} neighborhoods)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-sand-100 text-xs text-sand-400">
                  <th className="pb-3 pr-4 font-medium">Neighborhood</th>
                  <th className="pb-3 pr-4 font-medium text-right">Properties</th>
                  <th className="pb-3 pr-4 font-medium text-right">Avg Price</th>
                  <th className="pb-3 pr-4 font-medium text-right">Min Price</th>
                  <th className="pb-3 font-medium text-right">Max Price</th>
                </tr>
              </thead>
              <tbody>
                {neighborhoods.neighborhoods.map(
                  (n: { neighborhood: string; property_count: number; avg_price?: number; min_price?: number; max_price?: number }) => (
                    <tr key={n.neighborhood} className="border-b border-sand-50 hover:bg-sand-50">
                      <td className="py-2.5 pr-4 font-medium text-sand-800">{n.neighborhood}</td>
                      <td className="py-2.5 pr-4 text-right text-sand-600">{n.property_count}</td>
                      <td className="py-2.5 pr-4 text-right text-sand-600">{formatPrice(n.avg_price)}</td>
                      <td className="py-2.5 pr-4 text-right text-sand-600">{formatPrice(n.min_price)}</td>
                      <td className="py-2.5 text-right text-sand-600">{formatPrice(n.max_price)}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: string }) {
  return (
    <div className="rounded-xl border border-sand-200 bg-white p-5">
      <span className="text-2xl">{icon}</span>
      <p className="mt-3 text-2xl font-bold text-sand-900">{value}</p>
      <p className="mt-1 text-sm text-sand-500">{label}</p>
    </div>
  );
}

function BarItem({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="capitalize text-sand-700">{label}</span>
        <span className="text-sand-500">{value} ({Math.round(pct)}%)</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-sand-100">
        <div className="h-full rounded-full bg-aqar-400 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
