import type { Metadata } from "next";
import { SITE } from "@/lib/constants";
import { formatPlace } from "@/lib/format";
import { fetchPublicJob } from "@/lib/server-api";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }>; children: React.ReactNode };

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const job = await fetchPublicJob(id);
  if (!job) return { title: "Job not found", robots: { index: false } };
  const where = formatPlace(job.location, job.locality);
  const company = job.company?.name;
  return {
    title: [job.title, company].filter(Boolean).join(" at "),
    description: `${job.title}${company ? ` at ${company}` : ""}${where ? ` in ${where}` : ""}. ${job.description.slice(0, 140)}`,
    alternates: { canonical: `/jobs/${job.id}` },
  };
}

// Structured data so search engines can show the job in job-search results
function jobPostingJsonLd(job: NonNullable<Awaited<ReturnType<typeof fetchPublicJob>>>) {
  const unit = job.salary_period === "year" ? "YEAR" : "MONTH";
  const data: Record<string, unknown> = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    title: job.title,
    description: job.description,
    datePosted: job.created_at,
    hiringOrganization: { "@type": "Organization", name: job.company?.name || SITE.name },
    jobLocation: {
      "@type": "Place",
      address: { "@type": "PostalAddress", addressLocality: job.locality || job.location, addressRegion: job.location, addressCountry: "IN" },
    },
    employmentType: (job.employment_type || "full_time").toUpperCase(),
    url: `${SITE.url}/jobs/${job.id}`,
  };
  if (job.expires_at) data.validThrough = job.expires_at;
  if (job.salary_min || job.salary_max) {
    data.baseSalary = {
      "@type": "MonetaryAmount", currency: "INR",
      value: { "@type": "QuantitativeValue", minValue: job.salary_min ?? undefined, maxValue: job.salary_max ?? undefined, unitText: unit },
    };
  }
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

export default async function JobLayout({ params, children }: Props) {
  const { id } = await params;
  const job = await fetchPublicJob(id);
  return (
    <>
      {job && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jobPostingJsonLd(job) }} />}
      {children}
    </>
  );
}
