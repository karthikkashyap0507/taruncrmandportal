import type { Metadata } from "next";

// Landing page for the links in job-alert emails; keep it out of search results.
export const metadata: Metadata = {
  title: "Job alerts",
  robots: { index: false, follow: false },
};

export default function NewsletterLayout({ children }: { children: React.ReactNode }) {
  return children;
}
