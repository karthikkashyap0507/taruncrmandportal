"use client";

import { motion } from "framer-motion";
import { Building2 } from "lucide-react";
import { SectionHeading } from "@/components/shared/section-heading";
import { FEATURED_COMPANIES } from "@/lib/mock-data";

export function FeaturedCompanies() {
  return (
    <section className="border-y border-white/10 bg-[#111827]/50 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Top Employers"
          title="Featured Companies Hiring Now"
          description="Join teams at India's fastest-growing startups and global enterprises."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURED_COMPANIES.map((company, i) => (
            <motion.div
              key={company.id}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              whileHover={{ scale: 1.02 }}
              className="glass-card flex items-center gap-4 p-5"
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6]/30 to-[#8B5CF6]/30">
                <Building2 className="h-7 w-7 text-[#3B82F6]" />
              </div>
              <div>
                <h3 className="font-semibold text-white">{company.name}</h3>
                <p className="text-sm text-[#94A3B8]">{(company as any).industry}</p>
                <p className="mt-1 text-sm font-medium text-[#10B981]">
                  Hiring now
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
