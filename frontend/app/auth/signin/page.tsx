"use client";

import { motion } from "framer-motion";
import { Building2, GitBranch, Loader2, Mail, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { AxiosError } from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SITE } from "@/lib/constants";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import {
  forgotPassword,
  loginRequest,
  registerRequest,
} from "@/services/auth";
import { useAuthStore } from "@/store/auth-store";
import type { UserRole } from "@/types";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

const registerSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Enter a valid email"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    role: z.enum(["candidate", "recruiter", "company_admin"]),
    company_name: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.role !== "candidate") {
      const c = data.company_name?.trim() ?? "";
      if (c.length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Enter your company or organization name",
          path: ["company_name"],
        });
      }
    }
  });

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

function apiErrorMessage(err: unknown): string {
  const ax = err as AxiosError<{
    detail?: string | { msg: string; type?: string }[] | Record<string, unknown>;
  }>;
  const d = ax.response?.data?.detail;
  if (!d) return ax.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d
      .map((x) => {
        if (typeof x === "string") return x;
        if (x && typeof x === "object" && "msg" in x) return String((x as { msg: string }).msg);
        return JSON.stringify(x);
      })
      .join(", ");
  return "Request failed";
}

export default function SignInPage() {
  const router = useRouter();
  const setFromSuccess = useAuthStore((s) => s.setFromSuccess);
  const [banner, setBanner] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotResult, setForgotResult] = useState<string | null>(null);
  const [oauthMsg, setOauthMsg] = useState<string | null>(null);

  const loginForm = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const registerForm = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      role: "candidate",
      company_name: "",
    },
  });

  const regRole = registerForm.watch("role");

  const onLogin = async (data: LoginForm) => {
    setBanner(null);
    try {
      const res = await loginRequest(data.email, data.password);
      setFromSuccess(res);
      setBanner({ type: "ok", text: "Signed in successfully. Redirecting…" });
      router.push(dashboardPathForRole(res.user.role));
    } catch (e) {
      setBanner({ type: "err", text: apiErrorMessage(e) });
    }
  };

  const onRegister = async (data: RegisterForm) => {
    setBanner(null);
    try {
      const res = await registerRequest({
        name: data.name,
        email: data.email,
        password: data.password,
        role: data.role,
        company_name:
          data.role === "candidate" ? undefined : data.company_name?.trim(),
      });
      setFromSuccess(res);
      setBanner({ type: "ok", text: "Account created. Redirecting…" });
      router.push(dashboardPathForRole(res.user.role));
    } catch (e) {
      setBanner({ type: "err", text: apiErrorMessage(e) });
    }
  };

  const submitForgot = async () => {
    if (!forgotEmail.trim()) return;
    setForgotBusy(true);
    setForgotResult(null);
    try {
      const res = await forgotPassword(forgotEmail.trim());
      let msg = res.message;
      if (res.reset_token) {
        msg += ` Dev token (set DEBUG=true on API): ${res.reset_token}`;
      }
      setForgotResult(msg);
    } catch (e) {
      setForgotResult(apiErrorMessage(e));
    } finally {
      setForgotBusy(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden pb-24">
      <div className="absolute inset-0 hero-glow" />
      <motion.div
        className="absolute left-1/4 top-1/4 h-64 w-64 rounded-full bg-[#3B82F6]/20 blur-[100px]"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 6, repeat: Infinity }}
      />
      <motion.div
        className="absolute right-1/4 bottom-1/4 h-64 w-64 rounded-full bg-[#8B5CF6]/20 blur-[100px]"
        animate={{ scale: [1.2, 1, 1.2] }}
        transition={{ duration: 6, repeat: Infinity }}
      />

      <div className="relative mx-auto flex min-h-[calc(100vh-8rem)] max-w-md flex-col justify-center px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6 sm:p-8"
        >
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-white">Welcome to {SITE.name}</h1>
            <p className="mt-1 text-sm text-[#94A3B8]">{SITE.tagline}</p>
          </div>

          {oauthMsg && (
            <p className="mb-4 rounded-lg border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-3 py-2 text-center text-xs text-[#94A3B8]">
              {oauthMsg}
            </p>
          )}

          <div className="mb-6 grid grid-cols-3 gap-2">
            {[
              { icon: Mail, label: "Google", provider: "Google" },
              { icon: GitBranch, label: "GitHub", provider: "GitHub" },
              { icon: Building2, label: "LinkedIn", provider: "LinkedIn" },
            ].map((s) => (
              <Button
                key={s.label}
                variant="outline"
                className="border-white/10 bg-white/5 text-xs"
                type="button"
                onClick={() =>
                  setOauthMsg(
                    `${s.provider} sign-in requires OAuth client IDs in your environment. Use email & password for now, or configure GOOGLE / GITHUB / LINKEDIN keys on the API.`
                  )
                }
              >
                <s.icon className="mr-1 h-4 w-4" />
                {s.label}
              </Button>
            ))}
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/10" />
            </div>
            <p className="relative flex justify-center text-xs uppercase">
              <span className="bg-[#111827] px-2 text-[#94A3B8]">or continue with email</span>
            </p>
          </div>

          {banner && (
            <div
              className={`mb-4 rounded-lg px-3 py-2 text-sm ${
                banner.type === "ok"
                  ? "border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]"
                  : "border border-[#EF4444]/30 bg-[#EF4444]/10 text-[#FCA5A5]"
              }`}
            >
              {banner.text}
            </div>
          )}

          <Tabs defaultValue="login">
            <TabsList className="mb-6 grid w-full grid-cols-2 bg-white/5">
              <TabsTrigger value="login">Sign In</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={loginForm.handleSubmit(onLogin)} className="space-y-4">
                <div>
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    {...loginForm.register("email")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {loginForm.formState.errors.email && (
                    <p className="mt-1 text-xs text-[#EF4444]">
                      {loginForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="login-password">Password</Label>
                  <Input
                    id="login-password"
                    type="password"
                    autoComplete="current-password"
                    {...loginForm.register("password")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {loginForm.formState.errors.password && (
                    <p className="mt-1 text-xs text-[#EF4444]">
                      {loginForm.formState.errors.password.message}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setForgotEmail(loginForm.getValues("email") || "");
                    setForgotResult(null);
                    setForgotOpen(true);
                  }}
                  className="text-left text-xs text-[#3B82F6] hover:underline"
                >
                  Forgot password?
                </button>
                <Button
                  type="submit"
                  disabled={loginForm.formState.isSubmitting}
                  className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
                >
                  {loginForm.formState.isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Signing in…
                    </>
                  ) : (
                    "Sign In"
                  )}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={registerForm.handleSubmit(onRegister)} className="space-y-4">
                <div>
                  <Label htmlFor="reg-name">Full Name</Label>
                  <Input
                    id="reg-name"
                    autoComplete="name"
                    {...registerForm.register("name")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {registerForm.formState.errors.name && (
                    <p className="mt-1 text-xs text-[#EF4444]">
                      {registerForm.formState.errors.name.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="reg-email">Email</Label>
                  <Input
                    id="reg-email"
                    type="email"
                    autoComplete="email"
                    {...registerForm.register("email")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {registerForm.formState.errors.email && (
                    <p className="mt-1 text-xs text-[#EF4444]">
                      {registerForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div>
                  <Label htmlFor="reg-password">Password</Label>
                  <Input
                    id="reg-password"
                    type="password"
                    autoComplete="new-password"
                    {...registerForm.register("password")}
                    className="mt-1.5 border-white/10 bg-white/5"
                  />
                  {registerForm.formState.errors.password && (
                    <p className="mt-1 text-xs text-[#EF4444]">
                      {registerForm.formState.errors.password.message}
                    </p>
                  )}
                  <p className="mt-1 text-xs text-[#64748B]">At least 8 characters</p>
                </div>
                <div>
                  <Label>I am a</Label>
                  <Select
                    value={regRole}
                    onValueChange={(v) =>
                      registerForm.setValue("role", v as "candidate" | "recruiter" | "company_admin", { shouldValidate: true })
                    }
                  >
                    <SelectTrigger className="mt-1.5 border-white/10 bg-white/5">
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="candidate">Candidate (job seeker)</SelectItem>
                      <SelectItem value="recruiter">Recruiter</SelectItem>
                      <SelectItem value="company_admin">Company admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {regRole !== "candidate" && (
                  <div>
                    <Label htmlFor="reg-company">Company / organization name</Label>
                    <Input
                      id="reg-company"
                      placeholder="e.g. Acme Pvt Ltd"
                      {...registerForm.register("company_name")}
                      className="mt-1.5 border-white/10 bg-white/5"
                    />
                    {registerForm.formState.errors.company_name && (
                      <p className="mt-1 text-xs text-[#EF4444]">
                        {registerForm.formState.errors.company_name.message}
                      </p>
                    )}
                  </div>
                )}
                <Button
                  type="submit"
                  disabled={registerForm.formState.isSubmitting}
                  className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
                >
                  {registerForm.formState.isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating account…
                    </>
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>

          <p className="mt-6 text-center text-xs text-[#64748B]">
            By continuing you agree to our terms and privacy policy. Employer accounts require a
            verified company name so we can set up your workspace.
          </p>
        </motion.div>
      </div>

      <Dialog open={forgotOpen} onOpenChange={setForgotOpen}>
        <DialogContent className="border-white/10 bg-[#111827] text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reset password</DialogTitle>
            <DialogDescription className="text-[#94A3B8]">
              Enter your email. If an account exists, we will send reset instructions. With API{" "}
              <code className="text-[#3B82F6]">DEBUG=true</code>, the dev reset token is returned in
              the response for testing.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="forgot-email">Email</Label>
            <Input
              id="forgot-email"
              type="email"
              value={forgotEmail}
              onChange={(e) => setForgotEmail(e.target.value)}
              className="border-white/10 bg-white/5"
            />
          </div>
          {forgotResult && (
            <p className="rounded-md border border-white/10 bg-white/5 p-3 text-sm text-[#94A3B8]">
              {forgotResult}
            </p>
          )}
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="border-white/10" onClick={() => setForgotOpen(false)}>
              Close
            </Button>
            <Button
              className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
              disabled={forgotBusy}
              onClick={submitForgot}
            >
              {forgotBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send reset link"}
            </Button>
          </DialogFooter>
          <p className="text-center text-xs text-[#64748B]">
            Then open{" "}
            <Link href="/auth/reset-password" className="text-[#3B82F6] hover:underline">
              Reset password
            </Link>{" "}
            with your token.
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}
