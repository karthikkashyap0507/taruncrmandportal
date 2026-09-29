"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { NAV_LINKS } from "@/lib/constants";

/** Pre-load all main routes in the background so navigation feels instant */
export function RoutePrefetcher() {
  const router = useRouter();

  useEffect(() => {
    const routes = [
      ...NAV_LINKS.map((l) => l.href),
      "/auth/reset-password",
      "/dashboard/candidate",
      "/dashboard/recruiter",
      "/dashboard/company",
      "/dashboard/admin",
    ];
    routes.forEach((href) => {
      router.prefetch(href);
    });
  }, [router]);

  return null;
}
