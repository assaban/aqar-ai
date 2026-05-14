/**
 * Aqar.ai Unified API Client
 * Automatically handles SSR (Docker network) vs Browser context.
 */

const getBaseUrl = () => {
  // Server-side (inside Docker) uses the internal service name
  if (typeof window === "undefined") {
    return process.env.API_SERVER_URL || "http://api:8000";
  }
  // Client-side (browser) uses localhost
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
};

const API_BASE = getBaseUrl();

// ── Types ──────────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  city: string;
  country: string;
  is_verified: boolean;
  notes?: string;
  channels_count: number;
  created_at: string;
}

export interface ChannelRegistration {
  id: string;
  channel_url: string;
  channel_name?: string;
  status: 'pending' | 'approved' | 'rejected' | 'disabled';
  region: string;
  agent_name?: string;
  created_at: string;
}

export interface Property {
  id: string;
  video_source_id: string;
  property_type: string;
  listing_type: string;
  price?: number;
  price_currency: string;
  area_sqm?: number;
  title_generated?: string;
  description_generated?: string;
  extraction_confidence?: number;
  location?: { neighborhood?: string; city: string };
}

// ═══════════════════════════════════════
// Fetch Helpers
// ═══════════════════════════════════════

// 2. Update your apiFetch helper to handle Next.js cache options
export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { revalidate?: number }
): Promise<T> {
  const url = `${API_BASE}${path}`;

  // Extract revalidate if provided for Next.js Data Cache
  const { revalidate, ...restInit } = init || {};

  const response = await fetch(url, {
    ...restInit,
    next: revalidate !== undefined ? { revalidate } : undefined,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.text();
    console.error(`API fetch failed: ${url} (${response.status})`);
    throw new Error(`API error ${response.status}: ${body}`);
  }

  return response.json();
}

// ── Agent & Channel Methods ──────────────────────────────────────
export const agents = {
  list: () => apiFetch<Agent[]>("/api/v1/agents"),
  // ADD THESE:
  get: (id: string) => apiFetch<Agent>(`/api/v1/agents/${id}`),
  register: (data: Partial<Agent>) => apiFetch<Agent>("/api/v1/agents", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id: string, data: Partial<Agent>) => apiFetch<Agent>(`/api/v1/agents/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
};

export const channels = {
  list: (status?: string) => {
    const query = status ? `?status=${status}` : "";
    return apiFetch<ChannelRegistration[]>(`/api/v1/channels${query}`);
  },
  register: (data: { channel_url: string; agent_id?: string }) =>
    apiFetch<ChannelRegistration>("/api/v1/channels", {
      method: "POST",
      body: JSON.stringify(data)
    }),
  discover: (keywords: string) =>
    apiFetch("/api/v1/channels/discover", {
      method: "POST",
      body: JSON.stringify({ keywords })
    }),
};

export const geo = {
  getDefaults: () => apiFetch<{
    countries: string[];
    cities_by_country: Record<string, string[]>;
  }>("/api/v1/config/geo-defaults"),
};

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
