/**
 * Aqar.ai API Client
 *
 * Typed fetch helpers for communicating with the FastAPI backend.
 * Base URL configurable via NEXT_PUBLIC_API_URL environment variable.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ═══════════════════════════════════════
// Types
// ═══════════════════════════════════════

export interface Location {
  latitude: number;
  longitude: number;
  address_formatted?: string;
  neighborhood?: string;
  city: string;
  region: string;
}

export interface Property {
  id: string;
  video_source_id: string;
  property_type: string;
  listing_type: string;
  price?: number;
  price_currency: string;
  area_sqm?: number;
  rooms?: number;
  bedrooms?: number;
  bathrooms?: number;
  legal_status: string;
  title_generated?: string;
  description_generated?: string;
  floors?: number;
  has_garage?: boolean;
  has_garden?: boolean;
  has_elevator?: boolean;
  floor_number?: number;
  extraction_confidence?: number;
  is_published: boolean;
  location?: Location;
  created_at: string;
  updated_at: string;
}

export interface PropertyListResponse {
  items: Property[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface SearchHit {
  id: string;
  property_type: string;
  listing_type: string;
  title_generated: string;
  description_generated: string;
  price?: number;
  area_sqm?: number;
  rooms?: number;
  bedrooms?: number;
  neighborhood: string;
  city: string;
}

export interface SearchResponse {
  hits: SearchHit[];
  query: string;
  total: number;
  processing_time_ms: number;
  page: number;
  per_page: number;
}

export interface VideoSource {
  id: string;
  url: string;
  platform: string;
  title?: string;
  channel_name?: string;
  duration_seconds?: number;
  thumbnail_url?: string;
  published_at?: string;
  properties_count: number;
}

export interface VideoDetail extends VideoSource {
  transcript_text?: string;
  transcript_language?: string;
  transcript_confidence?: number;
  properties: Property[];
  processing_status?: string;
  processing_stage?: string;
  stage_timings?: Record<string, number>;
}

export interface NeighborhoodStat {
  neighborhood: string;
  property_count: number;
  avg_price?: number;
  min_price?: number;
  max_price?: number;
}

export interface Stats {
  total_videos: number;
  total_properties: number;
  total_published: number;
  processing_pending: number;
  processing_failed: number;
  processing_completed: number;
  avg_extraction_confidence?: number;
  property_types: Record<string, number>;
  listing_types: Record<string, number>;
}

export interface PipelineStatus {
  job_id: string;
  video_url: string;
  status: string;
  current_stage?: string;
  retry_count: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  stage_timings?: Record<string, number>;
}

// ═══════════════════════════════════════
// Fetch Helpers
// ═══════════════════════════════════════

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }

  return response.json();
}

// ═══════════════════════════════════════
// Properties
// ═══════════════════════════════════════

export interface PropertyFilters {
  property_type?: string;
  listing_type?: string;
  price_min?: number;
  price_max?: number;
  area_min?: number;
  area_max?: number;
  rooms_min?: number;
  neighborhood?: string;
  lat?: number;
  lng?: number;
  radius_km?: number;
  needs_review?: boolean;
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: string;
}

export async function fetchProperties(
  filters: PropertyFilters = {}
): Promise<PropertyListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  return apiFetch(`/api/v1/properties?${params.toString()}`);
}

export async function fetchProperty(id: string): Promise<Property> {
  return apiFetch(`/api/v1/properties/${id}`);
}

// ═══════════════════════════════════════
// Search
// ═══════════════════════════════════════

export interface SearchFilters {
  q?: string;
  property_type?: string;
  listing_type?: string;
  price_min?: number;
  price_max?: number;
  rooms_min?: number;
  neighborhood?: string;
  lat?: number;
  lng?: number;
  radius_km?: number;
  sort?: string;
  page?: number;
  per_page?: number;
}

export async function searchProperties(
  filters: SearchFilters = {}
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  return apiFetch(`/api/v1/search?${params.toString()}`);
}

// ═══════════════════════════════════════
// Stats
// ═══════════════════════════════════════

export async function fetchStats(): Promise<Stats> {
  return apiFetch("/api/v1/stats");
}

export async function fetchNeighborhoodStats(): Promise<{
  neighborhoods: NeighborhoodStat[];
  total_neighborhoods: number;
}> {
  return apiFetch("/api/v1/stats/neighborhoods");
}

// ═══════════════════════════════════════
// Videos
// ═══════════════════════════════════════

export async function fetchVideos(
  page = 1,
  per_page = 20
): Promise<{ items: VideoSource[]; total: number; has_next: boolean }> {
  return apiFetch(`/api/v1/videos?page=${page}&per_page=${per_page}`);
}

export async function fetchVideoDetail(id: string): Promise<VideoDetail> {
  return apiFetch(`/api/v1/videos/${id}`);
}

// ═══════════════════════════════════════
// Pipeline
// ═══════════════════════════════════════

export async function submitVideo(url: string): Promise<PipelineStatus> {
  return apiFetch("/api/v1/pipeline/submit", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function fetchPipelineStatus(
  jobId: string
): Promise<PipelineStatus> {
  return apiFetch(`/api/v1/pipeline/status/${jobId}`);
}
