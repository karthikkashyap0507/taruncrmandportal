"use client";

import { motion } from "framer-motion";
import { Loader2, Mail } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiError, publicApi } from "@/services/api";

type Msg = { type: "ok" | "err"; text: string };

function NewsletterAction() {
  const params = useSearchParams();
  const action = params.get("action");
  const email = params.get("email") || "";
  const sig = params.get("sig") || "";
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState(false);
  const confirmed = useRef(false);

  // Confirmation happens on arrival; unsubscribing waits for a click so that
  // link scanners in email clients can't unsubscribe anyone by accident.
  useEffect(() => {
    if (action !== "confirm" || confirmed.current) return;
    confirmed.current = true;
    if (!email || !sig) {
      setMsg({ type: "err", text: "This confirmation link is incomplete. Please subscribe again." });
      return;
    }
    setBusy(true);
    publicApi.confirmSubscription(email, sig)
      .then(r => setMsg({ type: "ok", text: r.data.message }))
      .catch(e => setMsg({ type: "err", text: apiError(e, "We couldn't confirm your subscription. Please try again.") }))
      .finally(() => setBusy(false));
  }, [action, email, sig]);

  const unsubscribe = async () => {
    setBusy(true);
    try {
      const r = await publicApi.unsubscribe(email, sig);
      setMsg({ type: "ok", text: r.data.message });
    } catch (e) {
      setMsg({ type: "err", text: apiError(e, "We couldn't unsubscribe you. Please try again.") });
    } finally {
      setBusy(false);
    }
  };

  const title = action === "unsubscribe" ? "Unsubscribe from job alerts" : "Job alerts";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card mx-auto max-w-md p-6 text-center sm:p-8"
    >
      <Mail className="mx-auto h-10 w-10 text-[#3B82F6]" />
      <h1 className="mt-4 font-heading text-2xl font-bold text-white">{title}</h1>

      {action === "unsubscribe" && !msg && (
        <>
          <p className="mt-2 text-sm text-[#94A3B8]">
            Stop the weekly job-alert emails to <span className="text-white">{email || "this address"}</span>?
          </p>
          <Button
            onClick={unsubscribe}
            disabled={busy || !email || !sig}
            className="mt-6 w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Unsubscribe"}
          </Button>
        </>
      )}

      {action === "confirm" && busy && (
        <p className="mt-4 flex items-center justify-center gap-2 text-sm text-[#94A3B8]">
          <Loader2 className="h-4 w-4 animate-spin" /> Confirming your subscription…
        </p>
      )}

      {action !== "confirm" && action !== "unsubscribe" && (
        <p className="mt-2 text-sm text-[#94A3B8]">
          Sign up for weekly job alerts at the bottom of the home page.
        </p>
      )}

      {msg && (
        <div
          role="status"
          className={`mt-4 rounded-lg px-3 py-2 text-sm ${
            msg.type === "ok"
              ? "border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]"
              : "border border-[#EF4444]/30 bg-[#EF4444]/10 text-[#FCA5A5]"
          }`}
        >
          {msg.text}
        </div>
      )}

      <Link href="/jobs" className="mt-6 inline-block text-sm text-[#3B82F6] hover:underline">
        Browse jobs →
      </Link>
    </motion.div>
  );
}

export default function NewsletterPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Suspense fallback={<div className="glass-card p-8 text-center text-[#94A3B8]">Loading…</div>}>
        <NewsletterAction />
      </Suspense>
    </div>
  );
}
