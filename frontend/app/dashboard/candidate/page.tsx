"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Bookmark, Briefcase, CheckCircle, FileText, Heart, LogOut, MessageSquare, Sparkles, TrendingUp, User, Zap } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { useAuthStore } from "@/store/auth-store";
import { externalJobsApi, jobsApi, messagesApi, savedJobsApi } from "@/services/api";
import { JobCard } from "@/components/shared/job-card";
import type { AppMessage, Application, ApplicationStatus, Job, MessageType, SavedJob } from "@/types";

const STATUS_CONFIG: Record<ApplicationStatus, { label: string; color: string; bg: string }> = {
  applied:   { label: "Applied",   color: "text-blue-400",   bg: "bg-blue-500/10 border-blue-500/20" },
  screening: { label: "Screening", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" },
  interview: { label: "Interview", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
  offered:   { label: "Offered",   color: "text-green-400",  bg: "bg-green-500/10 border-green-500/20" },
  hired:     { label: "Hired",     color: "text-emerald-300", bg: "bg-emerald-500/20 border-emerald-500/30" },
  withdrawn: { label: "Withdrawn", color: "text-slate-400",   bg: "bg-slate-500/10 border-slate-500/30" },
  rejected:  { label: "Rejected",  color: "text-red-400",    bg: "bg-red-500/10 border-red-500/20" },
};

export default function CandidateDashboardPage() {
  const router = useRouter();
  const { user, hydrated, logout } = useAuthStore();
  const [applications, setApplications] = useState<Application[]>([]);
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [recommendations, setRecommendations] = useState<Job[]>([]);
  const [inbox, setInbox] = useState<AppMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [savedLoading, setSavedLoading] = useState(false);
  const [unreadMessages, setUnreadMessages] = useState(0);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.replace("/auth/signin"); return; }
    if (user.role !== "candidate") { router.replace(dashboardPathForRole(user.role)); return; }
    loadData();
  }, [user, hydrated]);

  const loadData = async () => {
    setLoading(true);
    setSavedLoading(true);
    try {
      const [appsRes, savedRes, recRes, inboxRes] = await Promise.allSettled([
        jobsApi.listMyApplications(),
        savedJobsApi.list(),
        externalJobsApi.recommendations(),
        messagesApi.getInbox(),
      ]);
      if (appsRes.status === "fulfilled") setApplications(appsRes.value.data);
      if (savedRes.status === "fulfilled") setSavedJobs(savedRes.value.data);
      if (recRes.status === "fulfilled") setRecommendations(recRes.value.data);
      if (inboxRes.status === "fulfilled") {
        setInbox(inboxRes.value.data);
        setUnreadMessages(inboxRes.value.data.length);
      }
    } finally {
      setLoading(false);
      setSavedLoading(false);
    }
  };

  const handleUnsave = async (jobId: number) => {
    await savedJobsApi.unsave(jobId);
    setSavedJobs((prev) => prev.filter((s) => s.job_id !== jobId));
  };

  if (!hydrated || !user) return null;

  const stats = [
    { label: "Applications", value: applications.length, icon: Briefcase, color: "text-blue-400" },
    { label: "Interviews", value: applications.filter(a => a.status === "interview").length, icon: TrendingUp, color: "text-purple-400" },
    { label: "Offers", value: applications.filter(a => a.status === "offered").length, icon: Sparkles, color: "text-green-400" },
    { label: "Saved Jobs", value: savedJobs.length, icon: Bookmark, color: "text-yellow-400" },
  ];

  return (
    <div className="min-h-screen pb-24">
      {/* Header */}
      <div className="hero-glow border-b border-white/10 py-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] text-xl font-bold text-white">
                {user.name?.[0]?.toUpperCase() || "U"}
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-white">{user.name}</h1>
                <p className="text-[#94A3B8] text-sm">{user.email}</p>
                <Badge className="mt-1 border-0 bg-[#3B82F6]/20 text-[#3B82F6] capitalize">{user.role}</Badge>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Link href="/profile">
                <Button variant="outline" size="sm" className="border-white/10 bg-white/5">
                  <User className="mr-2 h-4 w-4" /> Profile
                </Button>
              </Link>
              <Link href="/resume-builder">
                <Button variant="outline" size="sm" className="border-white/10 bg-white/5">
                  <FileText className="mr-2 h-4 w-4" /> Resume Builder
                </Button>
              </Link>
              <Link href="/ats">
                <Button variant="outline" size="sm" className="border-white/10 bg-white/5">
                  <Briefcase className="mr-2 h-4 w-4" /> ATS Tracker
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={() => { logout(); router.replace("/"); }} className="text-red-400 hover:text-red-300 hover:bg-red-400/10">
                <LogOut className="mr-2 h-4 w-4" /> Logout
              </Button>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {stats.map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="glass-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-[#94A3B8]">{label}</p>
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <p className={`text-2xl font-bold ${color}`}>{loading ? "—" : value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Tabs defaultValue="applications">
          <TabsList className="mb-6 bg-white/5 border border-white/10">
            <TabsTrigger value="applications"><Briefcase className="mr-2 h-4 w-4" />Applications</TabsTrigger>
            <TabsTrigger value="messages" className="relative">
              <MessageSquare className="mr-2 h-4 w-4" />Messages
              {unreadMessages > 0 && <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">{unreadMessages}</span>}
            </TabsTrigger>
            <TabsTrigger value="saved"><Bookmark className="mr-2 h-4 w-4" />Saved Jobs</TabsTrigger>
            <TabsTrigger value="recommendations"><Sparkles className="mr-2 h-4 w-4" />Recommended</TabsTrigger>
          </TabsList>

          {/* Applications Tab */}
          <TabsContent value="applications">
            {loading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
              </div>
            ) : applications.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <Briefcase className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
                <h3 className="mb-2 font-semibold text-white">No applications yet</h3>
                <p className="mb-6 text-sm text-[#94A3B8]">Start applying to track your job search journey.</p>
                <Link href="/jobs">
                  <Button className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                    <Zap className="mr-2 h-4 w-4" /> Browse Jobs
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {applications.map((app) => {
                  const s = STATUS_CONFIG[app.status];
                  return (
                    <div key={app.id} className="glass-card flex items-center justify-between gap-4 p-4">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-[#3B82F6]/20 to-[#8B5CF6]/20 text-sm font-bold text-white">
                          #{app.job_id}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-white">Job #{app.job_id}</p>
                          <p className="text-xs text-[#94A3B8]">Applied {new Date(app.applied_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        {app.score !== null && app.score !== undefined && (
                          <span className="text-xs text-[#10B981]">{app.score}% match</span>
                        )}
                        <Badge className={`border ${s.bg} ${s.color}`}>{s.label}</Badge>
                        <Link href={`/jobs/${app.job_id}`}>
                          <Button size="sm" variant="outline" className="border-white/10 bg-white/5 text-xs">View Job</Button>
                        </Link>
                      </div>
                    </div>
                  );
                })}
                <div className="pt-2 text-center">
                  <Link href="/ats">
                    <Button variant="outline" className="border-white/10 bg-white/5">
                      <TrendingUp className="mr-2 h-4 w-4" /> Open ATS Pipeline View
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Messages Tab */}
          <TabsContent value="messages">
            {loading ? (
              <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="glass-card h-20 animate-pulse" />)}</div>
            ) : inbox.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <MessageSquare className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
                <h3 className="mb-2 font-semibold text-white">No messages yet</h3>
                <p className="text-sm text-[#94A3B8]">When recruiters send you messages, approvals, or interview invites, they'll appear here.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {inbox.map((msg) => {
                  const TYPE_CONFIG: Record<MessageType, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
                    message: { label: "Message", color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20", icon: <MessageSquare className="h-4 w-4" /> },
                    approval: { label: "Approved!", color: "text-green-400", bg: "bg-green-500/10 border-green-500/20", icon: <CheckCircle className="h-4 w-4" /> },
                    rejection: { label: "Rejected", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20", icon: <Bell className="h-4 w-4" /> },
                    interview_invite: { label: "Interview Invite!", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20", icon: <Sparkles className="h-4 w-4" /> },
                    offer: { label: "Job Offer!", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20", icon: <Zap className="h-4 w-4" /> },
                  };
                  const tc = TYPE_CONFIG[msg.message_type as MessageType] || TYPE_CONFIG.message;
                  return (
                    <div key={msg.id} className={`glass-card border p-4 ${tc.bg}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 flex-shrink-0 ${tc.color}`}>{tc.icon}</div>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-xs font-semibold ${tc.color}`}>{tc.label}</span>
                              <span className="text-xs text-[#64748B]">from {msg.sender_name}</span>
                              <span className="text-xs text-[#64748B]">•</span>
                              <span className="text-xs text-[#64748B]">{msg.job_title}</span>
                            </div>
                            <p className="text-sm text-white">{msg.content}</p>
                          </div>
                        </div>
                        <span className="flex-shrink-0 text-xs text-[#64748B]">
                          {new Date(msg.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* Saved Jobs Tab */}
          <TabsContent value="saved">
            {savedLoading ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-60 rounded-2xl" />)}
              </div>
            ) : savedJobs.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <Heart className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
                <h3 className="mb-2 font-semibold text-white">No saved jobs</h3>
                <p className="mb-6 text-sm text-[#94A3B8]">Bookmark jobs with the save button to find them here.</p>
                <Link href="/jobs">
                  <Button className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">Browse Jobs</Button>
                </Link>
              </div>
            ) : (
              <div className="grid gap-6 sm:grid-cols-2">
                {savedJobs.map((saved, i) => (
                  <JobCard key={saved.id} job={saved.job} index={i} initialSaved={true} />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Recommendations Tab */}
          <TabsContent value="recommendations">
            {loading ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-60 rounded-2xl" />)}
              </div>
            ) : recommendations.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <Sparkles className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
                <h3 className="mb-2 font-semibold text-white">No recommendations yet</h3>
                <p className="mb-6 text-sm text-[#94A3B8]">Add skills to your profile to get personalised job recommendations.</p>
                <Link href="/profile">
                  <Button className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">Update Profile</Button>
                </Link>
              </div>
            ) : (
              <>
                <p className="mb-4 text-sm text-[#94A3B8]">Jobs matched to your skills and experience.</p>
                <div className="grid gap-6 sm:grid-cols-2">
                  {recommendations.map((job, i) => <JobCard key={job.id} job={job} index={i} />)}
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
