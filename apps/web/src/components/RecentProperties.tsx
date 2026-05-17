"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchRecentProperties, type Property } from "@/lib/api";
import {
  formatPrice,
  formatArea,
  PROPERTY_TYPE_LABELS,
} from "@/lib/utils";

export function RecentProperties() {
  const [properties, setProperties] = useState<Property[]>([]);

  useEffect(() => {
    fetchRecentProperties(12).then(setProperties).catch(() => {});
  }, []);

  if (properties.length === 0) return null;

  return (
    <section className="py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-8 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-sand-900">Recently Added</h2>
          <Link
            href="/search"
            className="text-sm font-medium text-aqar-500 hover:text-aqar-600"
          >
            View all →
          </Link>
        </div>

        {/* Horizontal scroll container */}
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-sand-300 scrollbar-track-transparent">
          {properties.map((p) => (
            <Link
              key={p.id}
              href={`/property/${p.id}`}
              className="group w-72 shrink-0 overflow-hidden rounded-2xl border border-sand-200 bg-white transition-all hover:border-aqar-300 hover:shadow-lg"
            >
              {/* Color band based on type */}
              <div className="h-2 bg-gradient-to-r from-aqar-400 to-aqar-500" />

              <div className="p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="rounded-md bg-aqar-100 px-2 py-0.5 text-xs font-semibold text-aqar-700">
                    {PROPERTY_TYPE_LABELS[p.property_type] || p.property_type}
                  </span>
                  {p.extraction_confidence && p.extraction_confidence > 0.7 && (
                    <span className="flex h-2 w-2 rounded-full bg-emerald-400" title="High confidence" />
                  )}
                </div>

                <h3 className="mb-1 text-sm font-semibold text-sand-900 line-clamp-2 group-hover:text-aqar-600">
                  {p.title_generated || "Property listing"}
                </h3>

                {p.location && (
                  <p className="mb-2 text-xs text-sand-500">
                    📍 {p.location.neighborhood || p.location.city}
                  </p>
                )}

                <p className="text-lg font-bold text-aqar-600">
                  {formatPrice(p.price)}
                </p>

                <div className="mt-2 flex gap-2 text-xs text-sand-500">
                  {p.area_sqm && <span>{formatArea(p.area_sqm)}</span>}
                  {p.rooms && <span>{p.rooms} rooms</span>}
                  {p.bedrooms && <span>{p.bedrooms} bed</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
