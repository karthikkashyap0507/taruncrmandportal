"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { SectionHeading } from "@/components/shared/section-heading";
import { FAQ_ITEMS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export function FAQSection() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section className="py-20">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <SectionHeading eyebrow="FAQ" title="Frequently Asked Questions" />
        <div className="space-y-3">
          {FAQ_ITEMS.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-card overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between p-5 text-left"
                aria-expanded={open === i}
              >
                <span className="font-medium text-white">{item.q}</span>
                <span className="text-[#3B82F6]">{open === i ? "−" : "+"}</span>
              </button>
              <div
                className={cn(
                  "overflow-hidden transition-all",
                  open === i ? "max-h-48 pb-5 px-5" : "max-h-0"
                )}
              >
                <p className="text-sm text-[#94A3B8]">{item.a}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
