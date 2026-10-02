// Server-side calls to the API (pages, sitemap). On the server we can use the internal
// address (API_INTERNAL_URL) instead of going back out through the public website.
import type { Job } from "@/types";

export const SERVER_API_URL =
  process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchPublicJobs(params: Record<string, string | number> = {}): Promise<Job[]> {
  const qs = new URLSearchParams(Object.entries({ limit: 200, ...params }).map(([k, v]) => [k, String(v)]));
  try {
    const res = await fetch(`${SERVER_API_URL}/jobs?${qs}`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    return res.ok ? ((await res.json()) as Job[]) : [];
  } catch {
    return [];  // the page still renders; the browser can retry
  }
}

export async function fetchPublicJob(id: string | number): Promise<Job | null> {
  try {
    const res = await fetch(`${SERVER_API_URL}/jobs/${encodeURIComponent(String(id))}`,
      { cache: "no-store", signal: AbortSignal.timeout(8000) });
    return res.ok ? ((await res.json()) as Job) : null;
  } catch {
    return null;
  }
}

/** Every live job, page by page (for the sitemap). */
export async function fetchAllPublicJobs(max = 10000): Promise<Job[]> {
  const all: Job[] = [];
  for (let skip = 0; skip < max; skip += 200) {
    const page = await fetchPublicJobs({ skip, limit: 200 });
    all.push(...page);
    if (page.length < 200) break;
  }
  return all;
}
