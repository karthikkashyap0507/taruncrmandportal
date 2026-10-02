import type { Metadata } from "next";
import { fetchPublicJobs } from "@/lib/server-api";
import { JobsBrowser } from "./jobs-browser";

// Rendered on every request so the HTML always lists the current jobs (search engines,
// link previews and slow phones see real listings before any JavaScript runs).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Jobs",
  description: "Search verified jobs across India by qualification, city, area, experience and monthly pay.",
  alternates: { canonical: "/jobs" },
};

export default async function JobsPage() {
  const jobs = await fetchPublicJobs({ sort: "newest" });
  return <JobsBrowser initialJobs={jobs} />;
}
