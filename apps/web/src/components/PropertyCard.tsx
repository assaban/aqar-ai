import Link from "next/link";
import type { Property } from "@/lib/api";
import { formatPrice, formatArea, PROPERTY_TYPE_LABELS, LISTING_TYPE_LABELS, formatConfidence } from "@/lib/utils";

interface PropertyCardProps {
  property: Property;
}

export default function PropertyCard({ property }: PropertyCardProps) {
  const typeLabel = PROPERTY_TYPE_LABELS[property.property_type] || property.property_type;
  const listingLabel = LISTING_TYPE_LABELS[property.listing_type] || property.listing_type;

  return (
    <Link href={`/property/${property.id}`} className="group block overflow-hidden rounded-xl border border-sand-200 bg-white transition-all hover:border-aqar-300 hover:shadow-lg">
      <div className="flex items-center justify-between bg-sand-50 px-4 py-2.5">
        <span className="rounded-md bg-aqar-100 px-2 py-0.5 text-xs font-semibold text-aqar-700">{typeLabel}</span>

        {/* Platform Attribution Badge Request */}
        <div className="flex items-center gap-1.5 bg-white px-2 py-0.5 rounded border border-sand-200">
          <svg className="h-3 w-3 fill-red-600" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M23.498 6.163a3.003 3.003 0 0 0-2.11-2.11C19.517 3.545 12 3.545 12 3.545s-7.517 0-9.388.508a3.003 3.003 0 0 0-2.11 2.11C0 8.033 0 12 0 12s0 3.967.502 5.837a3.003 3.003 0 0 0 2.11 2.11c1.871.508 9.388.508 9.388.508s7.517 0 9.388-.508a3.003 3.003 0 0 0 2.11-2.11C24 15.967 24 12 24 12s0-3.967-.502-5.837zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
          </svg>
          <span className="text-[10px] font-bold text-sand-500 tracking-wider uppercase">YouTube Source</span>
        </div>
      </div>

      <div className="p-4">
        <h3 className="mb-1 text-base font-semibold text-sand-900 line-clamp-1 group-hover:text-aqar-600 transition-colors">
          {property.title_generated || "Untitled Property Tour"}
        </h3>

        {/* Source Agent Label Row Assignment */}
        <p className="text-xs text-sand-400 font-medium mb-2 flex items-center gap-1">
          <span>💼 Managed Listing</span>
        </p>

        {property.description_generated && (
          <p className="mb-3 text-xs leading-relaxed text-sand-500 line-clamp-2 bg-sand-50 p-2 rounded-lg border border-sand-100">
            <span className="font-bold text-aqar-600 block text-[10px] uppercase tracking-wider mb-0.5">AI Summary</span>
            {property.description_generated}
          </p>
        )}

        <div className="mb-3">
          <span className="text-xl font-bold text-aqar-600">{formatPrice(property.price, property.price_currency)}</span>
          {property.listing_type === "rent" && <span className="text-sm text-sand-400"> /month</span>}
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-sand-600 border-t border-sand-100 pt-3">
          {property.area_sqm && <span>📐 {formatArea(property.area_sqm)}</span>}
          {property.rooms && <span>🏠 {property.rooms} Rooms</span>}
          {property.bedrooms && <span>🛏️ {property.bedrooms} Bed</span>}
        </div>
      </div>
    </Link>
  );
}