/**
 * Aqar.ai API Configuration
 *
 * Server-side fetches (SSR) must use the Docker-internal API URL.
 * Client-side fetches (browser) use the public-facing URL.
 */

/** URL for server-side fetches (inside Docker network) */
export const API_SERVER =
  process.env.API_SERVER_URL || "http://api:8000";

/** URL for client-side fetches (browser) */
export const API_CLIENT =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch from the API, automatically choosing the right base URL
 * based on whether we are on the server or client.
 */
export async function serverFetch<T>(
  path: string,
  init?: RequestInit & { revalidate?: number }
): Promise<T | null> {
  const url = `${API_SERVER}${path}`;
  try {
    const res = await fetch(url, {
      ...init,
      next: init?.revalidate !== undefined ? { revalidate: init.revalidate } : undefined,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error(`API fetch failed: ${url}`, err);
    return null;
  }
}
