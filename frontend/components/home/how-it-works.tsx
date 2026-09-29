"use client";

import { motion } from "framer-motion";
import { SectionHeading } from "@/components/shared/section-heading";

const steps = [
  { step: "01", title: "Create Your Profile", desc: "Upload resume or build with AI. Get instant ATS scoring." },
  { step: "02", title: "AI Matches You", desc: "Semantic search finds roles aligned with your skills & goals." },
  { step: "03", title: "Apply in One Click", desc: "AI-generated cover letters and one-click applications." },
  { step: "04", title: "Land Your Dream Job", desc: "Track applications, schedule interviews, get career coaching." },
];

export function HowItWorks() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="How It Works"
          title="From Profile to Offer in 4 Steps"
        />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <motion.div
              key={s.step}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative"
            >
              <span className="text-5xl font-extrabold text-[#3B82F6]/20">{s.step}</span>
              <h3 className="mt-2 font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm text-[#94A3B8]">{s.desc}</p>
              {i < steps.length - 1 && (
                <div className="absolute -right-3 top-8 hidden h-0.5 w-6 bg-gradient-to-r from-[#3B82F6] to-transparent lg:block" />
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
