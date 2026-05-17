import { notFound } from "next/navigation";
import Link from "next/link";
import { serverFetch } from "@/lib/server-api";
import {
  formatPrice,
  formatArea,
  formatConfidence,
  PROPERTY_TYPE_LABELS,
  LISTING_TYPE_LABELS,
  LEGAL_STATUS_LABELS,
  getYouTubeEmbedUrl,
} from "@/lib/utils";
import type { Property, VideoDetail } from "@/lib/api";
import { PropertyEditor } from "@/components/PropertyEditor";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PropertyDetailPage({ params }: PageProps) {
  const { id } = await params;

  const property = await serverFetch<Property>(`/api/v1/properties/${id}`, { revalidate: 30 });
  if (!property) notFound();

  const video = property.video_source_id
    ? await serverFetch<VideoDetail>(`/api/v1/videos/${property.video_source_id}`, { revalidate: 60 })
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

      <div className="mb-6">
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="rounded-md bg-aqar-100 px-2.5 py-1 text-xs font-semibold text-aqar-700">{typeLabel}</span>
          <span className="rounded-md bg-sea-100 px-2.5 py-1 text-xs font-semibold text-sea-700">{listingLabel}</span>
          <span className="rounded-md bg-sand-200 px-2.5 py-1 text-xs font-medium text-sand-600">{legalLabel}</span>
          {property.needs_review && (
            <span className="rounded-md bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">Needs Review</span>
          )}
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
        <div className="lg:col-span-2 space-y-6">
          {/* Video embed */}
          {embedUrl && (
            <div className="overflow-hidden rounded-xl border border-sand-200">
              <div className="relative aspect-video">
                <iframe src={embedUrl} title="Property video" className="absolute inset-0 h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
              </div>
              {video?.title && <div className="bg-sand-50 px-4 py-2.5 text-sm text-sand-600">{video.title}</div>}
            </div>
          )}

          {/* Description */}
          {property.description_generated && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <h2 className="mb-3 text-lg font-semibold text-sand-900">Description</h2>
              <p className="leading-relaxed text-sand-600">{property.description_generated}</p>
            </div>
          )}

          {/* Details grid */}
          <div className="rounded-xl border border-sand-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold text-sand-900">Details</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {property.area_sqm && <DI label="Area" value={formatArea(property.area_sqm)} />}
              {property.rooms && <DI label="Rooms" value={String(property.rooms)} />}
              {property.bedrooms && <DI label="Bedrooms" value={String(property.bedrooms)} />}
              {property.bathrooms && <DI label="Bathrooms" value={String(property.bathrooms)} />}
              {property.floors && <DI label="Floors" value={String(property.floors)} />}
              {property.floor_number != null && <DI label="Floor" value={property.floor_number === 0 ? "Ground" : String(property.floor_number)} />}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {property.has_garage && <Badge icon="🚗" text="Garage" />}
              {property.has_garden && <Badge icon="🌿" text="Garden" />}
              {property.has_elevator && <Badge icon="🛗" text="Elevator" />}
            </div>
          </div>

          {/* Transcript */}
          {video?.transcript_text && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <h2 className="mb-3 text-lg font-semibold text-sand-900">Transcript</h2>
              <p className="text-sm leading-relaxed text-sand-500 line-clamp-8" dir="auto">{video.transcript_text}</p>
              <p className="mt-2 text-xs text-sand-400">
                Language: {video.transcript_language} | Confidence: {formatConfidence(video.transcript_confidence)}
              </p>
            </div>
          )}

          {/* Admin: Edit property */}
          <PropertyEditor propertyId={id} initialData={property} />
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="rounded-xl border border-aqar-200 bg-aqar-50 p-6">
            <p className="text-sm text-aqar-600">Price</p>
            <p className="text-2xl font-bold text-aqar-700">{formatPrice(property.price, property.price_currency)}</p>
            {property.listing_type === "rent" && <p className="text-sm text-aqar-500">per month</p>}
          </div>

          {property.extraction_confidence != null && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <p className="mb-2 text-sm font-medium text-sand-700">Data Confidence</p>
              <div className="mb-2 h-2 overflow-hidden rounded-full bg-sand-100">
                <div className={`h-full rounded-full ${property.extraction_confidence > 0.7 ? "bg-emerald-400" : property.extraction_confidence > 0.5 ? "bg-amber-400" : "bg-red-400"}`}
                  style={{ width: `${property.extraction_confidence * 100}%` }} />
              </div>
              <p className="text-xs text-sand-400">{formatConfidence(property.extraction_confidence)} (AI extraction)</p>
            </div>
          )}

          {video && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <p className="mb-2 text-sm font-medium text-sand-700">Source</p>
              <p className="text-sm text-sand-600">{video.channel_name || "Unknown"}</p>
              <a href={video.url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm text-sea-600 hover:text-sea-700">
                Watch on YouTube →
              </a>
            </div>
          )}

          {video?.stage_timings && (
            <div className="rounded-xl border border-sand-200 bg-white p-6">
              <p className="mb-2 text-sm font-medium text-sand-700">Processing</p>
              <div className="space-y-1 text-xs text-sand-500">
                {Object.entries(video.stage_timings).map(([stage, t]) => (
                  <div key={stage} className="flex justify-between">
                    <span className="capitalize">{stage.replace("_", " ")}</span>
                    <span>{(t as number).toFixed(1)}s</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DI({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs text-sand-400">{label}</p><p className="text-base font-semibold text-sand-800">{value}</p></div>;
}

function Badge({ icon, text }: { icon: string; text: string }) {
  return <span className="rounded-full bg-sand-100 px-3 py-1 text-xs text-sand-600">{icon} {text}</span>;
}
