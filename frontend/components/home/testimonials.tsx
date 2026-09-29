"use client";

import { motion } from "framer-motion";
import { Quote, Star } from "lucide-react";
import { SectionHeading } from "@/components/shared/section-heading";
import { TESTIMONIALS } from "@/lib/mock-data";

export function Testimonials() {
  return (
    <section className="border-y border-white/10 bg-[#111827]/30 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Success Stories"
          title="Loved by Candidates & Recruiters"
        />
        <div className="grid gap-6 md:grid-cols-3">
          {TESTIMONIALS.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass-card relative p-6"
            >
              <Quote className="absolute right-4 top-4 h-8 w-8 text-[#3B82F6]/20" />
              <div className="mb-3 flex gap-1">
                {Array.from({ length: t.rating }).map((_, j) => (
                  <Star key={j} className="h-4 w-4 fill-[#F59E0B] text-[#F59E0B]" />
                ))}
              </div>
              <p className="mb-4 text-sm text-[#94A3B8]">&ldquo;{t.quote}&rdquo;</p>
              <div>
                <p className="font-semibold text-white">{t.name}</p>
                <p className="text-xs text-[#94A3B8]">
                  {t.role} at {t.company}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
