"use client";

import { motion } from "framer-motion";
import { Mail } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Newsletter() {
  const [email, setEmail] = useState("");

  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="gradient-border glass-card mx-auto max-w-3xl rounded-3xl p-8 text-center sm:p-12"
        >
          <Mail className="mx-auto h-10 w-10 text-[#3B82F6]" />
          <h2 className="mt-4 font-heading text-2xl font-bold text-white sm:text-3xl">
            Get AI Job Alerts Weekly
          </h2>
          <p className="mt-2 text-[#94A3B8]">
            Personalized job matches delivered to your inbox. No spam, ever.
          </p>
          <form
            className="mx-auto mt-6 flex max-w-md flex-col gap-3 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              setEmail("");
            }}
          >
            <Input
              type="email"
              placeholder="you@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="border-white/10 bg-white/5"
            />
            <Button type="submit" className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
              Subscribe
            </Button>
          </form>
        </motion.div>
      </div>
    </section>
  );
}
