"use client";

import { PROPERTY_TYPE_LABELS, LISTING_TYPE_LABELS } from "@/lib/utils";

interface FilterState {
  property_type: string;
  listing_type: string;
  price_min: string;
  price_max: string;
  rooms_min: string;
  neighborhood: string;
}

interface SearchFiltersProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onReset: () => void;
}

export default function SearchFilters({
  filters,
  onChange,
  onReset,
}: SearchFiltersProps) {
  const update = (key: keyof FilterState, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-sand-800">Filters</h3>
        <button
          onClick={onReset}
          className="text-xs text-aqar-500 hover:text-aqar-700 transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Property Type */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-sand-600">
          Property Type
        </label>
        <select
          value={filters.property_type}
          onChange={(e) => update("property_type", e.target.value)}
          className="w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm text-sand-800 focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
        >
          <option value="">All</option>
          {Object.entries(PROPERTY_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Listing Type */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-sand-600">
          Listing Type
        </label>
        <select
          value={filters.listing_type}
          onChange={(e) => update("listing_type", e.target.value)}
          className="w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm text-sand-800 focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
        >
          <option value="">All</option>
          {Object.entries(LISTING_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Price Range */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-sand-600">
          Price (MAD)
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="Min"
            value={filters.price_min}
            onChange={(e) => update("price_min", e.target.value)}
            className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
          />
          <input
            type="number"
            placeholder="Max"
            value={filters.price_max}
            onChange={(e) => update("price_max", e.target.value)}
            className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
          />
        </div>
      </div>

      {/* Rooms */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-sand-600">
          Minimum Rooms
        </label>
        <select
          value={filters.rooms_min}
          onChange={(e) => update("rooms_min", e.target.value)}
          className="w-full rounded-lg border border-sand-200 bg-white px-3 py-2 text-sm text-sand-800 focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
        >
          <option value="">All</option>
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <option key={n} value={n}>
              {n}+
            </option>
          ))}
        </select>
      </div>

      {/* Neighborhood */}
      <div>
        <label className="mb-1.5 block text-xs font-medium text-sand-600">
          Neighborhood
        </label>
        <input
          type="text"
          placeholder="e.g. Iberia, Marshan..."
          value={filters.neighborhood}
          onChange={(e) => update("neighborhood", e.target.value)}
          className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm focus:border-aqar-400 focus:outline-none focus:ring-1 focus:ring-aqar-400"
        />
      </div>
    </div>
  );
}
