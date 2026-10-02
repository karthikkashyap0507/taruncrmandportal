import type { MetadataRoute } from "next";
import { SITE } from "@/lib/constants";
import { fetchAllPublicJobs } from "@/lib/server-api";

// Built on request so it always lists the jobs that are live right now
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const pages = ["", "/jobs", "/about", "/services", "/contact", "/privacy", "/terms"].map((route) => ({
    url: `${SITE.url}${route}`,
    lastModified: now,
    changeFrequency: (route === "/jobs" ? "daily" : "weekly") as "daily" | "weekly",
    priority: route === "" ? 1 : route === "/jobs" ? 0.9 : route === "/privacy" || route === "/terms" ? 0.3 : 0.7,
  }));
  const jobs = (await fetchAllPublicJobs()).map((job) => ({
    url: `${SITE.url}/jobs/${job.id}`,
    lastModified: new Date(job.updated_at || job.created_at || now),
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));
  return [...pages, ...jobs];
}
