"use client";

import { motion } from "framer-motion";
import { ArrowRight, Bot, Search, Sparkles, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AnimatedCounter } from "@/components/shared/animated-counter";
import { PLATFORM_STATS } from "@/lib/mock-data";

const floatingCards = [
  { label: "AI Match Score", value: "94%", x: "5%", y: "20%" },
  { label: "Jobs Applied Today", value: "2.4K", x: "75%", y: "15%" },
  { label: "Resume ATS Score", value: "87/100", x: "80%", y: "55%" },
];

export function HeroSection() {
  const [query, setQuery] = useState("");

  return (
    <section className="relative overflow-hidden hero-glow">
      <div className="absolute inset-0 -z-10">
        <motion.div
          className="absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-[#3B82F6]/20 blur-[120px]"
          animate={{ scale: [1, 1.1, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className="absolute right-0 top-1/3 h-[300px] w-[400px] rounded-full bg-[#8B5CF6]/20 blur-[100px]"
          animate={{ x: [0, 30, 0] }}
          transition={{ duration: 10, repeat: Infinity }}
        />
      </div>

      {floatingCards.map((card, i) => (
        <motion.div
          key={card.label}
          className="glass-card absolute hidden px-4 py-3 lg:block"
          style={{ left: card.x, top: card.y }}
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 3 + i, repeat: Infinity, delay: i * 0.5 }}
        >
          <p className="text-xs text-[#94A3B8]">{card.label}</p>
          <p className="text-lg font-bold gradient-text">{card.value}</p>
        </motion.div>
      ))}

      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8 lg:py-32">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-4xl text-center"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#3B82F6]/30 bg-[#3B82F6]/10 px-4 py-2 text-sm text-[#3B82F6]"
          >
            <Sparkles className="h-4 w-4" />
            Next Generation AI-Powered Hiring
          </motion.div>

          <h1 className="font-heading text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-7xl">
            Find Your Dream Job with{" "}
            <span className="gradient-text">AI Intelligence</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-[#94A3B8] sm:text-xl">
            JobsNexGen connects top talent with leading companies through smart
            matching, ATS tools, and AI career coaching — faster than ever.
          </p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mx-auto mt-10 max-w-2xl"
          >
            <div className="glass-card flex flex-col gap-3 p-2 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[#94A3B8]" />
                <Input
                  placeholder="Job title, skills, or company..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="border-0 bg-transparent pl-10 text-white placeholder:text-[#94A3B8] focus-visible:ring-0"
                />
              </div>
              <div className="relative flex-1">
                <Bot className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[#8B5CF6]" />
                <Input
                  placeholder="Location or Remote"
                  className="border-0 bg-transparent pl-10 text-white placeholder:text-[#94A3B8] focus-visible:ring-0"
                />
              </div>
              <Link href={`/jobs?q=${encodeURIComponent(query)}`}>
                <Button className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] px-8 sm:w-auto">
                  <Zap className="mr-2 h-4 w-4" />
                  AI Search
                </Button>
              </Link>
            </div>
          </motion.div>

          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link href="/jobs">
              <Button size="lg" className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] sm:w-auto">
                Browse Jobs
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link href="/auth/signin">
              <Button size="lg" variant="outline" className="w-full border-white/20 bg-white/5 sm:w-auto">
                Get Started Free
              </Button>
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mx-auto mt-20 grid max-w-4xl grid-cols-2 gap-6 sm:grid-cols-4"
        >
          {PLATFORM_STATS.map((stat) => (
            <div key={stat.label} className="glass-card p-4 text-center">
              <p className="text-2xl font-bold gradient-text sm:text-3xl">
                <AnimatedCounter value={stat.value} suffix={stat.suffix} />
              </p>
              <p className="mt-1 text-xs text-[#94A3B8] sm:text-sm">{stat.label}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
