"use client";
import { useState } from "react";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";
import { ArrowLeft } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch {
      toast.error("Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-brand-100">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <a href="/login" className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6">
            <ArrowLeft size={16} /> Back to login
          </a>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Reset Password</h1>
          <p className="text-sm text-gray-500 mb-6">
            Enter your email and we'll send a reset link.
          </p>

          {sent ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
              If this email exists in our system, a password reset link has been sent. Check your inbox.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="email"
                className="input"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
              <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
                {loading ? "Sending..." : "Send Reset Link"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
