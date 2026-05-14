
import { serverFetch } from "@/lib/server-api";

// Add these to apps/web/lib/api.ts

export interface Agent {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  city: string;
  is_verified: boolean;
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

// ── Agent Fetchers ──
export async function fetchAgents(): Promise<Agent[]> {
  return serverFetch("/api/v1/agents");
}

export async function registerAgent(data: Partial<Agent>): Promise<Agent> {
  return serverFetch("/api/v1/agents", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Channel Fetchers ──
export async function fetchChannels(status?: string): Promise<ChannelRegistration[]> {
  const url = status ? `/api/v1/channels?status=${status}` : "/api/v1/channels";
  return serverFetch(url);
}

export async function registerChannel(data: { channel_url: string; agent_id: string }): Promise<ChannelRegistration> {
  return serverFetch("/api/v1/channels", {
    method: "POST",
    body: JSON.stringify(data),
  });
}