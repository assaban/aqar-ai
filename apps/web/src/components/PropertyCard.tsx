import Link from "next/link";
import type { Property } from "@/lib/api";
import {
  formatPrice,
  formatArea,
  PROPERTY_TYPE_LABELS,
  LISTING_TYPE_LABELS,
  formatConfidence,
} from "@/lib/utils";

interface PropertyCardProps {
  property: Property;
}

export default function PropertyCard({ property }: PropertyCardProps) {
  const typeLabel =
    PROPERTY_TYPE_LABELS[property.property_type] || property.property_type;
  const listingLabel =
    LISTING_TYPE_LABELS[property.listing_type] || property.listing_type;

  return (
    <Link
      href={`/property/${property.id}`}
      className="group block overflow-hidden rounded-xl border border-sand-200 bg-white transition-all hover:border-aqar-300 hover:shadow-lg hover:shadow-aqar-100/50"
    >
      {/* Header band */}
      <div className="flex items-center justify-between bg-sand-50 px-4 py-2.5">
        <span className="rounded-md bg-aqar-100 px-2 py-0.5 text-xs font-semibold text-aqar-700">
          {typeLabel}
        </span>
        <span className="text-xs font-medium text-sand-500">
          {listingLabel}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="mb-2 text-base font-semibold text-sand-900 line-clamp-2 group-hover:text-aqar-600 transition-colors">
          {property.title_generated || "Untitled Property"}
        </h3>

        {/* Location */}
        {property.location && (
          <p className="mb-2 text-sm text-sand-500">
            📍 {property.location.neighborhood || property.location.city}
            {property.location.neighborhood && `, ${property.location.city}`}
          </p>
        )}

        {/* Summary snippet */}
        {property.description_generated && (
          <p className="mb-3 text-xs leading-relaxed text-sand-400 line-clamp-2">
            {property.description_generated}
          </p>
        )}

        {/* Price */}
        <div className="mb-3">
          <span className="text-xl font-bold text-aqar-600">
            {formatPrice(property.price, property.price_currency)}
          </span>
          {property.listing_type === "rent" && (
            <span className="text-sm text-sand-400"> /month</span>
          )}
        </div>

        {/* Attributes */}
        <div className="flex flex-wrap gap-3 text-sm text-sand-600">
          {property.area_sqm && (
            <span className="flex items-center gap-1">
              📐 {formatArea(property.area_sqm)}
            </span>
          )}
          {property.rooms && (
            <span className="flex items-center gap-1">
              🏠 {property.rooms} rooms
            </span>
          )}
          {property.bedrooms && (
            <span className="flex items-center gap-1">
              🛏️ {property.bedrooms} bed
            </span>
          )}
          {property.bathrooms && (
            <span className="flex items-center gap-1">
              🚿 {property.bathrooms} bath
            </span>
          )}
        </div>

        {/* Confidence badge */}
        {property.extraction_confidence && (
          <div className="mt-3 flex items-center gap-1.5">
            <div
              className={`h-2 w-2 rounded-full ${
                property.extraction_confidence > 0.7
                  ? "bg-emerald-400"
                  : property.extraction_confidence > 0.5
                    ? "bg-amber-400"
                    : "bg-red-400"
              }`}
            />
            <span className="text-xs text-sand-400">
              Confidence: {formatConfidence(property.extraction_confidence)}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}
