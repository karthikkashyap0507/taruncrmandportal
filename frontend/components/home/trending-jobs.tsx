"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { JobCard } from "@/components/shared/job-card";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { jobsApi } from "@/services/api";
import type { Job } from "@/types";

export function TrendingJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrendingJobs();
  }, []);

  const loadTrendingJobs = async () => {
    try {
      const res = await jobsApi.list();
      setJobs(res.data.slice(0, 4));
    } catch (err) {
      console.error("Failed to load trending jobs", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Trending Now"
          title="Hot Jobs Picked by AI"
          description="Roles trending across tech, design, and remote — matched to your profile in real time."
        />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-2">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-64 rounded-2xl" />
            ))
          ) : (
            jobs.map((job, i) => (
              <JobCard key={job.id} job={job} index={i} />
            ))
          )}
        </div>
        <div className="mt-10 text-center">
          <Link href="/jobs">
            <Button variant="outline" className="border-white/20 bg-white/5">
              View All Jobs
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
