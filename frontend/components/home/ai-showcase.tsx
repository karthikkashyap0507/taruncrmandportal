"use client";

import { motion } from "framer-motion";
import { Brain, FileSearch, MessageSquare, Target, Zap } from "lucide-react";
import { SectionHeading } from "@/components/shared/section-heading";

const features = [
  {
    icon: Brain,
    title: "AI Job Matching",
    description: "Semantic embeddings match you to roles you'll actually love.",
    color: "#3B82F6",
  },
  {
    icon: FileSearch,
    title: "Resume Parsing",
    description: "Extract skills, experience, and ATS scores instantly.",
    color: "#8B5CF6",
  },
  {
    icon: MessageSquare,
    title: "AI Career Coach",
    description: "Personalized feedback, interview tips, and growth roadmaps.",
    color: "#06B6D4",
  },
  {
    icon: Target,
    title: "Smart ATS",
    description: "Recruiters get AI-ranked candidates and pipeline analytics.",
    color: "#10B981",
  },
];

export function AIShowcase() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="AI-Powered"
          title="Hiring Intelligence Built In"
          description="Every feature is powered by cutting-edge AI — from search to interviews."
        />
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="glass-card group p-6"
            >
              <div
                className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${feature.color}20` }}
              >
                <feature.icon className="h-6 w-6" style={{ color: feature.color }} />
              </div>
              <h3 className="mb-2 font-semibold text-white">{feature.title}</h3>
              <p className="text-sm text-[#94A3B8]">{feature.description}</p>
              <Zap
                className="mt-4 h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100"
                style={{ color: feature.color }}
              />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
