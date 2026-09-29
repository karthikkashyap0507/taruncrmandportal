"use client";
import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";

function ResetForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) return toast.error("Passwords don't match");
    if (password.length < 8) return toast.error("Password must be at least 8 characters");
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      toast.success("Password reset! Please log in.");
      router.push("/login");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Reset failed. Link may be expired.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-brand-100">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <h1 className="text-xl font-bold text-gray-900 mb-2">Set New Password</h1>
          <p className="text-sm text-gray-500 mb-6">Choose a strong password for your account.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="password"
              className="input"
              placeholder="New password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoFocus
            />
            <input
              type="password"
              className="input"
              placeholder="Confirm new password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
              {loading ? "Resetting..." : "Reset Password"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
