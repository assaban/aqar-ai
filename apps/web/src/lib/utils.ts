/**
 * Aqar.ai Utility Helpers
 */

/** Format price with Moroccan Dirham */
export function formatPrice(price?: number | null, currency = "MAD"): string {
  if (!price) return "Price not available";
  return `${new Intl.NumberFormat("en").format(price)} ${currency}`;
}

/** Format area in square meters */
export function formatArea(area?: number | null): string {
  if (!area) return "";
  return `${area} m²`;
}

/** Property type labels */
export const PROPERTY_TYPE_LABELS: Record<string, string> = {
  apartment: "Apartment",
  house: "House",
  villa: "Villa",
  land: "Land",
  commercial: "Commercial",
  garage: "Garage",
  other: "Other",
};

/** Listing type labels */
export const LISTING_TYPE_LABELS: Record<string, string> = {
  sale: "For Sale",
  rent: "For Rent",
  unknown: "Not specified",
};

/** Legal status labels */
export const LEGAL_STATUS_LABELS: Record<string, string> = {
  tabou: "Title Deed (Tabou)",
  melkia: "Melkia",
  rasm: "Rasm",
  unknown: "Not specified",
};

/** Format a confidence score as percentage */
export function formatConfidence(confidence?: number | null): string {
  if (!confidence) return "";
  return `${Math.round(confidence * 100)}%`;
}

/** Format seconds to MM:SS */
export function formatDuration(seconds?: number | null): string {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Extract YouTube video ID from URL */
export function getYouTubeId(url: string): string | null {
  const match = url.match(
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/
  );
  return match ? match[1] : null;
}

/** YouTube embed URL */
export function getYouTubeEmbedUrl(url: string): string | null {
  const id = getYouTubeId(url);
  return id ? `https://www.youtube.com/embed/${id}` : null;
}
