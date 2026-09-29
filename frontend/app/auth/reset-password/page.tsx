"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { AxiosError } from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { resetPassword } from "@/services/auth";

const schema = z
  .object({
    token: z.string().min(10, "Paste the reset token from your email (or dev response)"),
    new_password: z.string().min(8, "At least 8 characters"),
    confirm: z.string().min(8),
  })
  .refine((d) => d.new_password === d.confirm, { message: "Passwords do not match", path: ["confirm"] });

type Form = z.infer<typeof schema>;

function apiErrorMessage(err: unknown): string {
  const ax = err as AxiosError<{ detail?: string | { msg: string }[] }>;
  const d = ax.response?.data?.detail;
  if (!d) return ax.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (typeof x === "string" ? x : x.msg)).join(", ");
  return "Request failed";
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tokenFromUrl = searchParams.get("token") ?? "";

  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: {
      token: tokenFromUrl,
      new_password: "",
      confirm: "",
    },
  });

  const { setValue } = form;

  useEffect(() => {
    if (tokenFromUrl) {
      setValue("token", tokenFromUrl);
    }
  }, [tokenFromUrl, setValue]);

  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const onSubmit = async (data: Form) => {
    setMsg(null);
    try {
      const res = await resetPassword(data.token.trim(), data.new_password);
      setMsg({ type: "ok", text: res.message });
      setTimeout(() => router.push("/auth/signin"), 2000);
    } catch (e) {
      setMsg({ type: "err", text: apiErrorMessage(e) });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card mx-auto max-w-md p-6 sm:p-8"
    >
      <h1 className="font-heading text-2xl font-bold text-white">Set new password</h1>
      <p className="mt-2 text-sm text-[#94A3B8]">
        Paste the secure token you received after requesting a reset (in development, the API may
        return the token in the JSON response when <code className="text-[#3B82F6]">DEBUG=true</code>
        ).
      </p>

      {msg && (
        <div
          className={`mt-4 rounded-lg px-3 py-2 text-sm ${
            msg.type === "ok"
              ? "border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]"
              : "border border-[#EF4444]/30 bg-[#EF4444]/10 text-[#FCA5A5]"
          }`}
        >
          {msg.text}
        </div>
      )}

      <form onSubmit={form.handleSubmit(onSubmit)} className="mt-6 space-y-4">
        <div>
          <Label htmlFor="token">Reset token</Label>
          <Input id="token" {...form.register("token")} className="mt-1.5 border-white/10 bg-white/5" />
          {form.formState.errors.token && (
            <p className="mt-1 text-xs text-[#EF4444]">{form.formState.errors.token.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="np">New password</Label>
          <Input
            id="np"
            type="password"
            autoComplete="new-password"
            {...form.register("new_password")}
            className="mt-1.5 border-white/10 bg-white/5"
          />
          {form.formState.errors.new_password && (
            <p className="mt-1 text-xs text-[#EF4444]">{form.formState.errors.new_password.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="cf">Confirm password</Label>
          <Input
            id="cf"
            type="password"
            autoComplete="new-password"
            {...form.register("confirm")}
            className="mt-1.5 border-white/10 bg-white/5"
          />
          {form.formState.errors.confirm && (
            <p className="mt-1 text-xs text-[#EF4444]">{form.formState.errors.confirm.message}</p>
          )}
        </div>
        <Button
          type="submit"
          disabled={form.formState.isSubmitting}
          className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
        >
          {form.formState.isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Update password"
          )}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-[#94A3B8]">
        <Link href="/auth/signin" className="text-[#3B82F6] hover:underline">
          Back to sign in
        </Link>
      </p>
    </motion.div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <Suspense
        fallback={
          <div className="glass-card p-8 text-center text-[#94A3B8]">Loading…</div>
        }
      >
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
