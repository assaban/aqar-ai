import { notFound } from "next/navigation";
import Link from "next/link";
import {
  formatPrice,
  formatArea,
  formatConfidence,
  PROPERTY_TYPE_LABELS,
  LISTING_TYPE_LABELS,
  LEGAL_STATUS_LABELS,
  getYouTubeEmbedUrl,
} from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PageProps {
  params: Promise<{ id: string }>;
}

async function getProperty(id: string) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/properties/${id}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function getVideo(videoSourceId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/videos/${videoSourceId}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PropertyDetailPage({ params }: PageProps) {
  const { id } = await params;
  const property = await getProperty(id);

  if (!property) notFound();

  const video = property.video_source_id
    ? await getVideo(property.video_source_id)
    : null;
  const embedUrl = video?.url ? getYouTubeEmbedUrl(video.url) : null;
  const typeLabel = PROPERTY_TYPE_LABELS[property.property_type] || property.property_type;
  const listingLabel = LISTING_TYPE_LABELS[property.listing_type] || property.listing_type;
  const legalLabel = LEGAL_STATUS_LABELS[property.legal_status] || property.legal_status;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {/* Breadcrumb */}
      <nav className="mb-6 text-sm text-sand-400">
        <Link href="/" className="hover:text-aqar-500">Home</Link>
        {" / "}
        <Link href="/search" className="hover:text-aqar-500">Search</Link>
        {" / "}
        <span className="text-sand-700">{typeLabel}</span>
      </nav>

      {/* Title and badges */}
      <div className="mb-6">
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="rounded-md bg-aqar-100 px-2.5 py-1 text-xs font-semibold text-aqar-700">
            {typeLabel}
          </span>
          <span className="rounded-md bg-sea-100 px-2.5 py-1 text-xs font-semibold text-sea-700">
            {listingLabel}
          </span>
          <span className="rounded-md bg-sand-200 px-2.5 py-1 text-xs font-medium text-sand-600">
            {legalLabel}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-sand-900 sm:text-3xl">
          {property.title_generated || `${typeLabel} in Tangier`}
        </h1>

        {property.location && (
          <p className="mt-2 text-sand-500">
            📍 {property.location.neighborhood || property.location.city}
            {property.location.neighborhood && `, ${property.location.city}`}
          </p>
        )}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video embed */}
          {embedUrl && (
            <div className="overflow-hidden rounded-xl border border-sand-200">
              <div className="relative aspect-video">
                <iframe
                  src={embedUrl}
                  title="Property video tour"
                  className="absolute inset-0 h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
          )}

          {/* Description */}
          {property.description_generated && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <h2 className="mb-3 text-lg font-semibold text-sand-900">Description</h2>
              <p className="leading-relaxed text-sand-600">
                {property.description_generated}
              </p>
            </div>
          )}

          {/* Attributes grid */}
          <div className="rounded-xl border border-sand-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-sand-900">Details</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {property.area_sqm && (
                <div>
                  <p className="text-xs text-sand-400">Area</p>
                  <p className="text-base font-semibold text-sand-800">{formatArea(property.area_sqm)}</p>
                </div>
              )}
              {property.rooms && (
                <div>
                  <p className="text-xs text-sand-400">Rooms</p>
                  <p className="text-base font-semibold text-sand-800">{property.rooms}</p>
                </div>
              )}
              {property.bedrooms && (
                <div>
                  <p className="text-xs text-sand-400">Bedrooms</p>
                  <p className="text-base font-semibold text-sand-800">{property.bedrooms}</p>
                </div>
              )}
              {property.bathrooms && (
                <div>
                  <p className="text-xs text-sand-400">Bathrooms</p>
                  <p className="text-base font-semibold text-sand-800">{property.bathrooms}</p>
                </div>
              )}
              {property.floors && (
                <div>
                  <p className="text-xs text-sand-400">Floors</p>
                  <p className="text-base font-semibold text-sand-800">{property.floors}</p>
                </div>
              )}
              {property.floor_number != null && (
                <div>
                  <p className="text-xs text-sand-400">Floor</p>
                  <p className="text-base font-semibold text-sand-800">
                    {property.floor_number === 0 ? "Ground" : property.floor_number}
                  </p>
                </div>
              )}
            </div>

            {/* Amenities */}
            <div className="mt-4 flex flex-wrap gap-2">
              {property.has_garage && (
                <span className="rounded-full bg-sand-100 px-3 py-1 text-xs text-sand-600">🚗 Garage</span>
              )}
              {property.has_garden && (
                <span className="rounded-full bg-sand-100 px-3 py-1 text-xs text-sand-600">🌿 Garden</span>
              )}
              {property.has_elevator && (
                <span className="rounded-full bg-sand-100 px-3 py-1 text-xs text-sand-600">🛗 Elevator</span>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Price card */}
          <div className="rounded-xl border border-aqar-200 bg-aqar-50 p-6">
            <p className="text-sm text-aqar-600">Price</p>
            <p className="text-2xl font-bold text-aqar-700">
              {formatPrice(property.price, property.price_currency)}
            </p>
            {property.listing_type === "rent" && (
              <p className="text-sm text-aqar-500">per month</p>
            )}
          </div>

          {/* Confidence indicator */}
          {property.extraction_confidence != null && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <p className="mb-2 text-sm font-medium text-sand-700">Data Confidence</p>
              <div className="mb-2 h-2 overflow-hidden rounded-full bg-sand-100">
                <div
                  className={`h-full rounded-full transition-all ${
                    property.extraction_confidence > 0.7
                      ? "bg-emerald-400"
                      : property.extraction_confidence > 0.5
                        ? "bg-amber-400"
                        : "bg-red-400"
                  }`}
                  style={{ width: `${property.extraction_confidence * 100}%` }}
                />
              </div>
              <p className="text-xs text-sand-400">
                {formatConfidence(property.extraction_confidence)} confidence
                (automated AI extraction)
              </p>
            </div>
          )}

          {/* Source video info */}
          {video && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <p className="mb-2 text-sm font-medium text-sand-700">Source Video</p>
              <p className="text-sm text-sand-600">
                {video.channel_name || "Unknown channel"}
              </p>
              {video.title && (
                <p className="mt-1 text-xs text-sand-400 line-clamp-2">{video.title}</p>
              )}
              <a
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-block text-sm text-sea-600 hover:text-sea-700"
              >
                Watch on YouTube →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
