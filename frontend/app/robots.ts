import type { MetadataRoute } from "next";
import { SITE } from "@/lib/constants";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private or personal pages have nothing for search engines
      disallow: ["/api/", "/dashboard/", "/auth/", "/profile", "/ats", "/resume-builder", "/newsletter"],
    },
    sitemap: `${SITE.url}/sitemap.xml`,
    host: SITE.url,
  };
}
