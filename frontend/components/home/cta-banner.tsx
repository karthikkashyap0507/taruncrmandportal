"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function CTABanner() {
  return (
    <section className="pb-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#3B82F6] via-[#8B5CF6] to-[#06B6D4] p-8 sm:p-12"
        >
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4xIj48cGF0aCBkPSJNMzYgMzRoLTJ2LTRoMnY0em0wLTZoLTJ2LTRoMnY0em0tNiA2aC00di0yaDR2MnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-30" />
          <div className="relative text-center">
            <h2 className="font-heading text-2xl font-bold text-white sm:text-4xl">
              Ready to Transform Your Career?
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-white/80">
              Join 420,000+ professionals who found their dream roles with JobsNexGen AI.
            </p>
            <Link href="/auth/signin">
              <Button size="lg" className="mt-6 bg-white text-[#3B82F6] hover:bg-white/90">
                Start Free Today
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
