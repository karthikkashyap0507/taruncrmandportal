"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { SectionHeading } from "@/components/shared/section-heading";
import { JOB_CATEGORIES } from "@/lib/mock-data";

export function Categories() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Explore"
          title="Browse by Category"
        />
        <div className="flex flex-wrap justify-center gap-3">
          {JOB_CATEGORIES.map((cat, i) => (
            <motion.div
              key={cat}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.03 }}
              whileHover={{ scale: 1.05 }}
            >
              <Link
                href={`/jobs?category=${encodeURIComponent(cat)}`}
                className="glass-card inline-block rounded-full px-5 py-2.5 text-sm font-medium text-white transition-colors hover:border-[#3B82F6]/50"
              >
                {cat}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
