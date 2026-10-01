"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Briefcase, Building2, Calendar, ChevronRight, ExternalLink,
  Loader2, RefreshCw, TrendingUp, User, Zap
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { jobsApi, apiError } from "@/services/api";
import { useAuthStore } from "@/store/auth-store";
import type { Application, ApplicationStatus } from "@/types";

const STAGES: { key: ApplicationStatus; label: string; color: string; bg: string; icon: string }[] = [
  { key: "applied",   label: "Applied",   color: "text-blue-400",   bg: "bg-blue-500/10 border-blue-500/30",   icon: "📩" },
  { key: "screening", label: "Screening", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/30", icon: "🔍" },
  { key: "interview", label: "Interview", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/30", icon: "🎯" },
  { key: "offered",   label: "Offered",   color: "text-green-400",  bg: "bg-green-500/10 border-green-500/30",  icon: "🎉" },
  { key: "hired",     label: "Hired",     color: "text-emerald-300", bg: "bg-emerald-500/10 border-emerald-500/30", icon: "🏆" },
  { key: "rejected",  label: "Rejected",  color: "text-red-400",    bg: "bg-red-500/10 border-red-500/30",    icon: "❌" },
];

const NEXT_STAGE: Record<ApplicationStatus, ApplicationStatus | null> = {
  applied: "screening",
  screening: "interview",
  interview: "offered",
  offered: "hired",
  rejected: null,
  hired: null,
  withdrawn: null,
};

export default function ATSPage() {
  const router = useRouter();
  const { user, hydrated } = useAuthStore();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [movingId, setMovingId] = useState<number | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.replace("/auth/signin"); return; }
    loadApplications();
  }, [hydrated, user]);

  const loadApplications = async () => {
    setLoading(true);
    try {
      const res = await jobsApi.listMyApplications();
      setApplications(res.data);
    } catch (e) {
      console.error("Failed to load applications", e);
    } finally {
      setLoading(false);
    }
  };

  const moveStage = async (appId: number, newStatus: ApplicationStatus) => {
    setMovingId(appId);
    try {
      await jobsApi.updateApplication(appId, { status: newStatus });
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, status: newStatus } : a))
      );
      if (selectedApp?.id === appId) setSelectedApp((a) => a ? { ...a, status: newStatus } : a);
    } catch (e) {
      alert(apiError(e, "Could not move this application"));
    } finally {
      setMovingId(null);
    }
  };

  const totalApps = applications.length;
  const activeApps = applications.filter(a => !["rejected"].includes(a.status)).length;
  const interviewApps = applications.filter(a => a.status === "interview").length;
  const offerApps = applications.filter(a => a.status === "offered").length;

  if (!hydrated || !user) {
    return <div className="flex min-h-[50vh] items-center justify-center text-[#94A3B8]">Loading…</div>;
  }

  return (
    <div className="min-h-screen pb-24">
      {/* Header */}
      <div className="hero-glow border-b border-white/10 py-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#3B82F6]/30 bg-[#3B82F6]/10 px-3 py-1 text-xs text-[#3B82F6]">
                <Briefcase className="h-3 w-3" /> ATS Tracker
              </div>
              <h1 className="font-heading text-3xl font-bold text-white lg:text-4xl">Application Pipeline</h1>
              <p className="mt-2 text-[#94A3B8]">Track every application through the hiring stages in real time.</p>
            </div>
            <Button variant="outline" className="border-white/10 bg-white/5" onClick={loadApplications} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          {/* Stats */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Total Applied", value: totalApps, color: "text-blue-400" },
              { label: "Active", value: activeApps, color: "text-yellow-400" },
              { label: "Interviews", value: interviewApps, color: "text-purple-400" },
              { label: "Offers", value: offerApps, color: "text-green-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="glass-card p-4 text-center">
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-[#94A3B8]">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="mx-auto max-w-full overflow-x-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex min-w-max gap-4">
          {STAGES.map((stage) => {
            const stageApps = applications.filter((a) => a.status === stage.key);
            return (
              <div key={stage.key} className="w-72 flex-shrink-0">
                <div className={`mb-3 flex items-center justify-between rounded-xl border px-4 py-3 ${stage.bg}`}>
                  <span className={`font-semibold flex items-center gap-2 ${stage.color}`}>
                    <span>{stage.icon}</span> {stage.label}
                  </span>
                  <Badge className={`border-0 ${stage.bg} ${stage.color}`}>{stageApps.length}</Badge>
                </div>

                <div className="space-y-3">
                  {loading ? (
                    Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-2xl" />)
                  ) : stageApps.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-white/10 p-6 text-center text-sm text-[#94A3B8]">
                      No applications
                    </div>
                  ) : (
                    stageApps.map((app, i) => (
                      <motion.div
                        key={app.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="glass-card p-4 cursor-pointer hover:border-white/20 transition-all"
                        onClick={() => setSelectedApp(app)}
                      >
                        <div className="mb-2 flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-[#3B82F6]/20 to-[#8B5CF6]/20 text-sm font-bold text-white">
                              {String(app.job_id).slice(-2)}
                            </div>
                            <div>
                              <p className="text-sm font-semibold text-white line-clamp-1">Job #{app.job_id}</p>
                              <p className="text-xs text-[#94A3B8]">App #{app.id}</p>
                            </div>
                          </div>
                          {movingId === app.id && <Loader2 className="h-4 w-4 animate-spin text-[#3B82F6]" />}
                        </div>

                        <div className="flex items-center gap-1 mb-3">
                          <Calendar className="h-3 w-3 text-[#64748B]" />
                          <p className="text-xs text-[#64748B]">
                            Applied {new Date(app.applied_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                          </p>
                        </div>

                        {app.score !== undefined && app.score !== null && (
                          <div className="mb-3 flex items-center gap-2">
                            <TrendingUp className="h-3 w-3 text-[#10B981]" />
                            <span className="text-xs text-[#10B981]">Match score: {app.score}%</span>
                          </div>
                        )}

                        {/* Move stage buttons — candidates can't move, recruiters can */}
                        {user.role !== "candidate" && NEXT_STAGE[stage.key] && (
                          <button
                            onClick={(e) => { e.stopPropagation(); moveStage(app.id, NEXT_STAGE[stage.key]!); }}
                            disabled={movingId === app.id}
                            className={`w-full flex items-center justify-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
                              STAGES.find(s => s.key === NEXT_STAGE[stage.key])?.bg
                            } ${STAGES.find(s => s.key === NEXT_STAGE[stage.key])?.color} hover:opacity-80`}
                          >
                            <ChevronRight className="h-3 w-3" />
                            Move to {STAGES.find(s => s.key === NEXT_STAGE[stage.key])?.label}
                          </button>
                        )}
                        {user.role !== "candidate" && stage.key !== "rejected" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); moveStage(app.id, "rejected"); }}
                            disabled={movingId === app.id}
                            className="mt-1 w-full flex items-center justify-center gap-1 rounded-lg px-2 py-1 text-xs text-red-400 hover:bg-red-400/10 transition-colors"
                          >
                            Reject
                          </button>
                        )}
                      </motion.div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Empty state */}
      {!loading && applications.length === 0 && (
        <div className="mx-auto max-w-md px-4 py-16 text-center">
          <div className="glass-card p-12">
            <Briefcase className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
            <h3 className="mb-2 text-xl font-semibold text-white">No applications yet</h3>
            <p className="mb-6 text-[#94A3B8]">
              {user.role === "candidate"
                ? "Start applying to jobs to track them here."
                : "Post jobs to start receiving applications."}
            </p>
            <Button
              onClick={() => router.push(user.role === "candidate" ? "/jobs" : "/dashboard/recruiter")}
              className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
            >
              <Zap className="mr-2 h-4 w-4" />
              {user.role === "candidate" ? "Browse Jobs" : "Post a Job"}
            </Button>
          </div>
        </div>
      )}

      {/* Application detail panel */}
      <AnimatePresence>
        {selectedApp && (
          <motion.div
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
            className="fixed inset-y-0 right-0 z-50 w-80 bg-[#0F172A] border-l border-white/10 shadow-2xl overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-white">Application Detail</h3>
                <button onClick={() => setSelectedApp(null)} className="text-[#94A3B8] hover:text-white">✕</button>
              </div>
              <div className="space-y-4">
                <div className="glass-card p-4">
                  <p className="text-xs text-[#94A3B8] mb-1">Job ID</p>
                  <p className="text-white font-semibold">#{selectedApp.job_id}</p>
                </div>
                <div className="glass-card p-4">
                  <p className="text-xs text-[#94A3B8] mb-1">Status</p>
                  <Badge className={`${STAGES.find(s => s.key === selectedApp.status)?.bg} ${STAGES.find(s => s.key === selectedApp.status)?.color} border-0`}>
                    {STAGES.find(s => s.key === selectedApp.status)?.icon} {selectedApp.status}
                  </Badge>
                </div>
                <div className="glass-card p-4">
                  <p className="text-xs text-[#94A3B8] mb-1">Applied On</p>
                  <p className="text-white">{new Date(selectedApp.applied_at).toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}</p>
                </div>
                {selectedApp.score !== null && selectedApp.score !== undefined && (
                  <div className="glass-card p-4">
                    <p className="text-xs text-[#94A3B8] mb-1">Match Score</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-white/10 rounded-full h-2">
                        <div style={{ width: `${selectedApp.score}%` }} className="h-full bg-gradient-to-r from-[#3B82F6] to-[#10B981] rounded-full" />
                      </div>
                      <span className="text-[#10B981] font-semibold">{selectedApp.score}%</span>
                    </div>
                  </div>
                )}
                <a href={`/jobs/${selectedApp.job_id}`} target="_blank" rel="noopener noreferrer"
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-white/10 bg-white/5 px-4 py-2 text-sm text-white hover:bg-white/10 transition-colors">
                  <ExternalLink className="h-4 w-4" /> View Job
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
