"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import PropertyCard from "@/components/PropertyCard";
import SearchFilters from "@/components/SearchFilters";
import { fetchProperties, type Property, type PropertyFilters } from "@/lib/api";

// Dynamic import for Leaflet (client-only, no SSR)
const PropertyMap = dynamic(() => import("@/components/PropertyMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[400px] items-center justify-center rounded-xl bg-sand-100 text-sand-400">
      Loading map...
    </div>
  ),
});

const DEFAULT_FILTERS = {
  property_type: "",
  listing_type: "",
  price_min: "",
  price_max: "",
  rooms_min: "",
  neighborhood: "",
};

export default function SearchPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [properties, setProperties] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showMap, setShowMap] = useState(false);
  const [query, setQuery] = useState(searchParams.get("q") || "");
  const [filters, setFilters] = useState({
    ...DEFAULT_FILTERS,
    property_type: searchParams.get("property_type") || "",
    listing_type: searchParams.get("listing_type") || "",
  });

  const loadProperties = useCallback(async () => {
    setLoading(true);
    try {
      const apiFilters: PropertyFilters = {
        page,
        per_page: 20,
        sort_by: "created_at",
        sort_order: "desc",
      };

      if (filters.property_type) apiFilters.property_type = filters.property_type;
      if (filters.listing_type) apiFilters.listing_type = filters.listing_type;
      if (filters.price_min) apiFilters.price_min = Number(filters.price_min);
      if (filters.price_max) apiFilters.price_max = Number(filters.price_max);
      if (filters.rooms_min) apiFilters.rooms_min = Number(filters.rooms_min);
      if (filters.neighborhood) apiFilters.neighborhood = filters.neighborhood;

      const data = await fetchProperties(apiFilters);
      setProperties(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to load properties:", err);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    loadProperties();
  }, [loadProperties]);

  const handleFilterChange = (newFilters: typeof filters) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handleReset = () => {
    setFilters(DEFAULT_FILTERS);
    setQuery("");
    setPage(1);
  };

  const propertiesWithLocation = properties.filter((p) => p.location);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Search bar */}
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search: apartment, villa, neighborhood..."
          className="flex-1 rounded-xl border border-sand-200 bg-white px-5 py-3 text-sand-800 shadow-sm placeholder:text-sand-400 focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
        />
        <button
          onClick={() => loadProperties()}
          className="rounded-xl bg-aqar-500 px-6 py-3 font-semibold text-white transition-colors hover:bg-aqar-600"
        >
          Search
        </button>
      </div>

      <div className="flex gap-6">
        {/* Sidebar filters */}
        <aside className="hidden w-64 shrink-0 lg:block">
          <div className="sticky top-20 rounded-xl border border-sand-200 bg-white p-5">
            <SearchFilters
              filters={filters}
              onChange={handleFilterChange}
              onReset={handleReset}
            />
          </div>
        </aside>

        {/* Main content */}
        <div className="flex-1">
          {/* Results header */}
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-sand-500">
              {loading ? "Loading..." : `${total} property(ies) found`}
            </p>
            <button
              onClick={() => setShowMap(!showMap)}
              className="rounded-lg border border-sand-200 px-3 py-1.5 text-sm font-medium text-sand-600 transition-colors hover:bg-sand-50"
            >
              {showMap ? "Hide map" : "Show map"}
            </button>
          </div>

          {/* Map */}
          {showMap && propertiesWithLocation.length > 0 && (
            <div className="mb-6">
              <PropertyMap properties={propertiesWithLocation} />
            </div>
          )}

          {/* Results grid */}
          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-64 animate-pulse rounded-xl bg-sand-100"
                />
              ))}
            </div>
          ) : properties.length === 0 ? (
            <div className="rounded-xl border border-sand-200 bg-white py-16 text-center">
              <p className="text-lg text-sand-500">No properties found</p>
              <p className="mt-2 text-sm text-sand-400">
                Try adjusting your filters
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {properties.map((p) => (
                <PropertyCard key={p.id} property={p} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {total > 20 && (
            <div className="mt-8 flex justify-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded-lg border border-sand-200 px-4 py-2 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="flex items-center px-4 text-sm text-sand-500">
                Page {page} / {Math.ceil(total / 20)}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page * 20 >= total}
                className="rounded-lg border border-sand-200 px-4 py-2 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
