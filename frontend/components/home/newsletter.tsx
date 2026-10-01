"use client";

import { motion } from "framer-motion";
import { Mail } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiError, publicApi } from "@/services/api";

export function Newsletter() {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  const subscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setResult(null);
    try {
      const res = await publicApi.subscribe(email.trim());
      setResult({ ok: true, text: res.data.message });
      setEmail("");
    } catch (err) {
      setResult({ ok: false, text: apiError(err, "Couldn't subscribe right now. Please try again.") });
    } finally {
      setSending(false);
    }
  };

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
            The newest jobs on JobsNexGen, in your inbox every Monday. No spam, ever.
          </p>
          <form className="mx-auto mt-6 flex max-w-md flex-col gap-3 sm:flex-row" onSubmit={subscribe}>
            <Input
              type="email"
              placeholder="you@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="border-white/10 bg-white/5"
            />
            <Button type="submit" disabled={sending} className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
              {sending ? "Subscribing..." : "Subscribe"}
            </Button>
          </form>
          {result && (
            <p role="status" className={`mt-4 text-sm ${result.ok ? "text-[#4ADE80]" : "text-[#F87171]"}`}>
              {result.text}
            </p>
          )}
        </motion.div>
      </div>
    </section>
  );
}
