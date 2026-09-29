"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart2, Briefcase, CheckCircle, ChevronDown, ChevronUp,
  Download, Edit, Eye, LogOut, Mail, MessageSquare, Phone,
  Plus, RefreshCw, Send, Sparkles, Trash2, TrendingUp, User, Users, XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { useAuthStore } from "@/store/auth-store";
import { jobsApi, messagesApi } from "@/services/api";
import type { Application, ApplicationStatus, AppMessage, ATSResult, Job, JobCreate, JobUpdate, MessageType } from "@/types";

// ─── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<ApplicationStatus, { label: string; color: string; bg: string }> = {
  applied:   { label: "Applied",   color: "text-blue-400",   bg: "bg-blue-500/20 border-blue-500/30" },
  screening: { label: "Screening", color: "text-yellow-400", bg: "bg-yellow-500/20 border-yellow-500/30" },
  interview: { label: "Interview", color: "text-purple-400", bg: "bg-purple-500/20 border-purple-500/30" },
  offered:   { label: "Offered",   color: "text-green-400",  bg: "bg-green-500/20 border-green-500/30" },
  rejected:  { label: "Rejected",  color: "text-red-400",    bg: "bg-red-500/20 border-red-500/30" },
};

// ─── ATS score helpers ────────────────────────────────────────────────────────
function scoreColor(score: number) {
  if (score >= 70) return { ring: "ring-green-500", bar: "bg-green-500", text: "text-green-400", label: "Excellent" };
  if (score >= 50) return { ring: "ring-yellow-500", bar: "bg-yellow-500", text: "text-yellow-400", label: "Good" };
  if (score >= 30) return { ring: "ring-orange-500", bar: "bg-orange-500", text: "text-orange-400", label: "Fair" };
  return { ring: "ring-red-500", bar: "bg-red-500", text: "text-red-400", label: "Poor" };
}

function ScoreRing({ score }: { score: number }) {
  const { text } = scoreColor(score);
  const r = 20, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div className="relative flex flex-col items-center justify-center">
      <svg width="56" height="56" className="-rotate-90">
        <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle cx="28" cy="28" r={r} fill="none" stroke="currentColor"
          strokeWidth="5" strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round" className={text} style={{ transition: "stroke-dasharray 0.6s ease" }} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-sm font-bold leading-none ${text}`}>{score}</span>
      </div>
    </div>
  );
}

function ScoreBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-[#94A3B8]">{label}</span>
        <span className="text-white font-medium">{value}/{max}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function RecruiterDashboardPage() {
  const router = useRouter();
  const { user, hydrated, logout } = useAuthStore();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Record<number, Application[]>>({});
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [messages, setMessages] = useState<AppMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("message");
  const [sendingMsg, setSendingMsg] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [createForm, setCreateForm] = useState<JobCreate>({ title: "", description: "", skills: [], status: "published" });
  const [editForm, setEditForm] = useState<JobUpdate>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("jobs");
  const [highlightedJob, setHighlightedJob] = useState<number | null>(null);

  // ATS tracker state
  const [atsData, setAtsData] = useState<Record<number, ATSResult[]>>({});  // jobId → results
  const [atsApps, setAtsApps] = useState<Record<number, Application[]>>({}); // jobId → apps
  const [atsLoading, setAtsLoading] = useState<Record<number, boolean>>({});
  const [expandedApp, setExpandedApp] = useState<number | null>(null);
  const [atsJobFilter, setAtsJobFilter] = useState<number | "all">("all");
  const [atsSortDir, setAtsSortDir] = useState<"desc" | "asc">("desc");

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.replace("/auth/signin"); return; }
    if (user.role !== "recruiter" && user.role !== "company_admin") {
      router.replace(dashboardPathForRole(user.role)); return;
    }
    loadJobs();
  }, [user, hydrated]);

  const loadJobs = async () => {
    try {
      const res = await jobsApi.listMy();
      setJobs(res.data);
    } finally {
      setLoading(false);
    }
  };

  const loadApplications = async (jobId: number) => {
    try {
      const res = await jobsApi.listApplications(jobId);
      setApplications(prev => ({ ...prev, [jobId]: res.data }));
    } catch (e) { console.error(e); }
  };

  const loadMessages = async (appId: number) => {
    try {
      const res = await messagesApi.getForApplication(appId);
      setMessages(res.data);
    } catch { setMessages([]); }
  };

  const selectApp = async (app: Application) => {
    setSelectedApp(app);
    setMessages([]);
    await loadMessages(app.id);
  };

  const sendMessage = async () => {
    if (!selectedApp || !newMessage.trim()) return;
    setSendingMsg(true);
    try {
      const res = await messagesApi.send(selectedApp.id, newMessage.trim(), messageType);
      setMessages(prev => [...prev, res.data]);
      setNewMessage("");
      if (selectedApp.job_id) await loadApplications(selectedApp.job_id);
    } finally { setSendingMsg(false); }
  };

  const handleStatusChange = async (appId: number, status: ApplicationStatus) => {
    await jobsApi.updateApplication(appId, { status });
    Object.keys(applications).forEach(jid => loadApplications(parseInt(jid)));
    if (selectedApp?.id === appId) setSelectedApp(a => a ? { ...a, status } : a);
  };

  const handleCreateJob = async () => {
    try {
      await jobsApi.create(createForm);
      setIsCreateOpen(false);
      setCreateForm({ title: "", description: "", skills: [], status: "published" });
      loadJobs();
    } catch (e) { console.error(e); }
  };

  const handleEditJob = async () => {
    if (!editingJob) return;
    try {
      await jobsApi.update(editingJob.id, editForm);
      setIsEditOpen(false);
      loadJobs();
    } catch (e) { console.error(e); }
  };

  const handleDeleteJob = async (jobId: number) => {
    if (!confirm("Delete this job?")) return;
    await jobsApi.delete(jobId);
    loadJobs();
  };

  // ── ATS helpers ────────────────────────────────────────────────────────────
  const loadATSForJob = async (jobId: number) => {
    setAtsLoading(prev => ({ ...prev, [jobId]: true }));
    try {
      // Load apps first (to get candidate info)
      const appsRes = await jobsApi.listApplications(jobId);
      setAtsApps(prev => ({ ...prev, [jobId]: appsRes.data }));
      // Compute scores for all
      const scoreRes = await jobsApi.computeATSAll(jobId);
      const resultsMap: Record<number, ATSResult> = {};
      for (const r of scoreRes.data.results) resultsMap[r.application_id] = r;
      // Merge scores back into apps
      const updatedApps = appsRes.data.map(a => ({
        ...a,
        score: resultsMap[a.id]?.total ?? a.score,
      }));
      setAtsApps(prev => ({ ...prev, [jobId]: updatedApps }));
      setAtsData(prev => ({ ...prev, [jobId]: scoreRes.data.results }));
    } catch (e) { console.error(e); }
    finally { setAtsLoading(prev => ({ ...prev, [jobId]: false })); }
  };

  const getATSResult = (jobId: number, appId: number): ATSResult | undefined =>
    atsData[jobId]?.find(r => r.application_id === appId);

  // Flattened sorted list for the selected job filter
  const atsRows: Array<{ job: Job; app: Application; result?: ATSResult }> = [];
  for (const job of jobs) {
    if (atsJobFilter !== "all" && job.id !== atsJobFilter) continue;
    const apps = atsApps[job.id] ?? [];
    for (const app of apps) {
      atsRows.push({ job, app, result: getATSResult(job.id, app.id) });
    }
  }
  atsRows.sort((a, b) => {
    const sa = a.result?.total ?? a.app.score ?? -1;
    const sb = b.result?.total ?? b.app.score ?? -1;
    return atsSortDir === "desc" ? sb - sa : sa - sb;
  });

  if (!hydrated || !user) return null;

  const allApps = Object.values(applications).flat();
  const stats = [
    { label: "Jobs Posted",      value: jobs.length,                                           icon: Briefcase,   color: "text-blue-400" },
    { label: "Total Applicants", value: allApps.length,                                        icon: Users,       color: "text-purple-400" },
    { label: "Interviews",       value: allApps.filter(a => a.status === "interview").length,  icon: TrendingUp,  color: "text-cyan-400" },
    { label: "Offers Sent",      value: allApps.filter(a => a.status === "offered").length,    icon: Sparkles,    color: "text-green-400" },
  ];

  return (
    <div className="min-h-screen pb-24">
      {/* ── Header ── */}
      <div className="hero-glow border-b border-white/10 py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#8B5CF6] to-[#06B6D4]">
                <Briefcase className="h-7 w-7 text-white" />
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-white">{user.name}</h1>
                <p className="text-sm text-[#94A3B8]">Recruiter Dashboard</p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger render={
                  <Button className="bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4]">
                    <Plus className="mr-2 h-4 w-4" /> Post Job
                  </Button>
                } />
                <JobFormDialog title="Post a New Job" form={createForm} setForm={setCreateForm as any}
                  onSubmit={handleCreateJob} onCancel={() => setIsCreateOpen(false)} />
              </Dialog>
              <Button variant="ghost" onClick={() => { logout(); router.push("/"); }}
                className="text-red-400 hover:text-red-300 hover:bg-red-400/10">
                <LogOut className="mr-2 h-4 w-4" /> Sign out
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

      {/* ── Main content ── */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 bg-white/5 border border-white/10">
            <TabsTrigger value="jobs"><Briefcase className="mr-2 h-4 w-4" />My Jobs ({jobs.length})</TabsTrigger>
            <TabsTrigger value="applications"><Users className="mr-2 h-4 w-4" />Applications</TabsTrigger>
            <TabsTrigger value="ats"><BarChart2 className="mr-2 h-4 w-4" />ATS Tracker</TabsTrigger>
          </TabsList>

          {/* ── My Jobs ── */}
          <TabsContent value="jobs">
            {loading ? (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {[1,2,3].map(i => <div key={i} className="glass-card h-48 animate-pulse" />)}
              </div>
            ) : jobs.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <Briefcase className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">No jobs posted yet</h3>
                <Button onClick={() => setIsCreateOpen(true)} className="bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4]">
                  <Plus className="mr-2 h-4 w-4" /> Post Your First Job
                </Button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {jobs.map(job => (
                  <Card key={job.id} className="bg-white/5 border-white/10 hover:border-white/20 transition-all">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-white text-lg">{job.title}</CardTitle>
                          <CardDescription className="text-[#94A3B8]">
                            {job.location || "Remote"} • {job.employment_type?.replace("_"," ") || "Full Time"}
                          </CardDescription>
                        </div>
                        <Badge className={job.status === "published" ? "bg-green-500/20 text-green-400" : job.status === "draft" ? "bg-yellow-500/20 text-yellow-400" : "bg-red-500/20 text-red-400"}>
                          {job.status}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-[#94A3B8] text-sm line-clamp-2 mb-3">{job.description}</p>
                      <div className="flex flex-wrap gap-1">
                        {job.skills?.slice(0,3).map((s,i) => (
                          <Badge key={i} variant="secondary" className="bg-white/10 text-white text-xs">{s}</Badge>
                        ))}
                      </div>
                    </CardContent>
                    <CardFooter className="flex gap-2">
                      <Button variant="outline" size="sm" className="border-white/10 flex-1" onClick={() => {
                        setEditingJob(job);
                        setEditForm({ title: job.title, description: job.description, salary_min: job.salary_min, salary_max: job.salary_max, skills: job.skills, experience_level: job.experience_level, location: job.location, employment_type: job.employment_type, status: job.status });
                        setIsEditOpen(true);
                      }}>
                        <Edit className="mr-1 h-3 w-3" /> Edit
                      </Button>
                      <Button variant="outline" size="sm" className="border-white/10" onClick={async () => {
                        await loadApplications(job.id);
                        setHighlightedJob(job.id);
                        setActiveTab("applications");
                      }}>
                        <Eye className="h-3 w-3" />
                      </Button>
                      <Button variant="outline" size="sm" className="border-white/10 text-red-400 hover:bg-red-500/10" onClick={() => handleDeleteJob(job.id)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* ── Applications ── */}
          <TabsContent value="applications">
            <div className="grid gap-6 lg:grid-cols-5">
              <div className="lg:col-span-2 space-y-4">
                {jobs.map(job => (
                  <div key={job.id} className={`glass-card transition-all ${highlightedJob === job.id ? "ring-2 ring-[#8B5CF6]/60" : ""}`}>
                    <div className="flex items-center justify-between p-4">
                      <div>
                        <p className="font-semibold text-white text-sm">{job.title}</p>
                        <p className="text-xs text-[#94A3B8]">{applications[job.id]?.length ?? "?"} applicants</p>
                      </div>
                      <Button size="sm" variant="outline" className="border-white/10 bg-white/5" onClick={async () => {
                        await loadApplications(job.id);
                        setHighlightedJob(job.id);
                      }}>
                        <RefreshCw className="mr-1 h-3 w-3" /> Refresh
                      </Button>
                    </div>
                    {applications[job.id] && (
                      <div className="border-t border-white/10">
                        {applications[job.id].length === 0 ? (
                          <p className="p-4 text-center text-xs text-[#94A3B8]">No applications yet</p>
                        ) : applications[job.id].map(app => {
                          const s = STATUS_CONFIG[app.status];
                          const isSelected = selectedApp?.id === app.id;
                          return (
                            <div key={app.id} onClick={() => selectApp(app)}
                              className={`cursor-pointer border-b border-white/5 p-4 transition-colors last:border-0 ${isSelected ? "bg-[#3B82F6]/10" : "hover:bg-white/5"}`}>
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6]/30 to-[#8B5CF6]/30 text-xs font-bold text-white">
                                    {(app.full_name || app.candidate_info?.name || "C")[0].toUpperCase()}
                                  </div>
                                  <div>
                                    <p className="text-sm font-medium text-white">{app.full_name || app.candidate_info?.name || `Candidate #${app.candidate_id}`}</p>
                                    <p className="text-xs text-[#94A3B8]">{app.years_experience ? `${app.years_experience} yrs exp` : ""}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  {app.score != null && (
                                    <span className={`text-xs font-bold ${scoreColor(app.score).text}`}>{Math.round(app.score)}%</span>
                                  )}
                                  <Badge className={`text-xs border ${s.bg} ${s.color}`}>{app.status}</Badge>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {jobs.length === 0 && (
                  <div className="glass-card p-8 text-center">
                    <Users className="mx-auto mb-3 h-10 w-10 text-[#94A3B8]" />
                    <p className="text-sm text-[#94A3B8]">Post a job to see applications here.</p>
                  </div>
                )}
              </div>

              {/* Candidate detail panel */}
              <div className="lg:col-span-3">
                {!selectedApp ? (
                  <div className="glass-card flex flex-col items-center justify-center p-12 text-center h-64">
                    <User className="mb-3 h-10 w-10 text-[#64748B]" />
                    <p className="text-[#94A3B8]">Select an applicant to view their details</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="glass-card p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] text-xl font-bold text-white">
                            {(selectedApp.full_name || selectedApp.candidate_info?.name || "C")[0].toUpperCase()}
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-white">{selectedApp.full_name || selectedApp.candidate_info?.name || `Candidate #${selectedApp.candidate_id}`}</h3>
                            {selectedApp.candidate_info?.headline && <p className="text-sm text-[#94A3B8]">{selectedApp.candidate_info.headline}</p>}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {selectedApp.score != null && (
                            <div className={`rounded-full border px-3 py-1 text-xs font-bold ${scoreColor(Math.round(selectedApp.score)).text} border-current`}>
                              ATS {Math.round(selectedApp.score)}%
                            </div>
                          )}
                          <div className={`rounded-full border px-3 py-1 text-xs font-medium ${STATUS_CONFIG[selectedApp.status].bg} ${STATUS_CONFIG[selectedApp.status].color}`}>
                            {selectedApp.status}
                          </div>
                        </div>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2 text-sm mb-4">
                        {selectedApp.candidate_info?.email && (
                          <div className="flex items-center gap-2 text-[#94A3B8]">
                            <Mail className="h-4 w-4 text-[#3B82F6]" />
                            <a href={`mailto:${selectedApp.candidate_info.email}`} className="hover:text-white transition-colors">{selectedApp.candidate_info.email}</a>
                          </div>
                        )}
                        {selectedApp.phone && (
                          <div className="flex items-center gap-2 text-[#94A3B8]">
                            <Phone className="h-4 w-4 text-[#8B5CF6]" />
                            <span>{selectedApp.phone}</span>
                          </div>
                        )}
                        {selectedApp.years_experience != null && (
                          <div className="flex items-center gap-2 text-[#94A3B8]">
                            <Briefcase className="h-4 w-4 text-[#06B6D4]" />
                            <span>{selectedApp.years_experience} years experience</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-[#94A3B8]">
                          <User className="h-4 w-4 text-[#F59E0B]" />
                          <span>Applied {new Date(selectedApp.applied_at).toLocaleDateString("en-IN", { day:"numeric", month:"short", year:"numeric" })}</span>
                        </div>
                      </div>

                      {(selectedApp.candidate_info?.skills?.length ?? 0) > 0 && (
                        <div className="mb-4">
                          <p className="text-xs text-[#64748B] mb-2">Skills</p>
                          <div className="flex flex-wrap gap-1.5">
                            {(selectedApp.candidate_info?.skills || []).map((s,i) => (
                              <Badge key={i} variant="outline" className="border-white/10 bg-white/5 text-xs text-[#94A3B8]">{s}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {selectedApp.cover_letter && (
                        <div className="mb-4">
                          <p className="text-xs text-[#64748B] mb-2">Cover Letter</p>
                          <div className="rounded-lg bg-white/5 border border-white/10 p-3">
                            <p className="text-sm text-[#94A3B8] whitespace-pre-wrap">{selectedApp.cover_letter}</p>
                          </div>
                        </div>
                      )}

                      {(selectedApp.resume_url || selectedApp.candidate_info?.resume_url) && (
                        <div className="mb-4">
                          <a href={selectedApp.resume_url || selectedApp.candidate_info?.resume_url}
                            target="_blank" rel="noopener noreferrer" download
                            className="inline-flex items-center gap-2 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/30 px-4 py-2 text-sm text-[#3B82F6] hover:bg-[#3B82F6]/20 transition-colors">
                            <Download className="h-4 w-4" /> Download Resume
                          </a>
                        </div>
                      )}

                      <div className="border-t border-white/10 pt-4">
                        <p className="text-xs text-[#64748B] mb-2">Update Status</p>
                        <div className="flex flex-wrap gap-2">
                          {[
                            { status: "screening" as ApplicationStatus, label: "Move to Screening", icon: <Eye className="h-3 w-3" />, cls: "text-yellow-400 border-yellow-500/30 bg-yellow-500/10 hover:bg-yellow-500/20" },
                            { status: "interview" as ApplicationStatus, label: "Invite to Interview", icon: <MessageSquare className="h-3 w-3" />, cls: "text-purple-400 border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20" },
                            { status: "offered" as ApplicationStatus, label: "Send Offer", icon: <CheckCircle className="h-3 w-3" />, cls: "text-green-400 border-green-500/30 bg-green-500/10 hover:bg-green-500/20" },
                            { status: "rejected" as ApplicationStatus, label: "Reject", icon: <XCircle className="h-3 w-3" />, cls: "text-red-400 border-red-500/30 bg-red-500/10 hover:bg-red-500/20" },
                          ].map(({ status, label, icon, cls }) => (
                            <button key={status} onClick={() => handleStatusChange(selectedApp.id, status)}
                              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${cls}`}>
                              {icon} {label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Messaging */}
                    <div className="glass-card p-5">
                      <h4 className="font-semibold text-white mb-4 flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-[#3B82F6]" /> Messages
                      </h4>
                      <div className="space-y-3 mb-4 max-h-48 overflow-y-auto">
                        {messages.length === 0 ? (
                          <p className="text-center text-xs text-[#64748B] py-4">No messages yet.</p>
                        ) : messages.map(msg => (
                          <div key={msg.id} className={`flex ${msg.sender_id === parseInt(user?.id?.toString() || "0") ? "justify-end" : "justify-start"}`}>
                            <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${msg.sender_id === parseInt(user?.id?.toString() || "0") ? "bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] text-white" : "bg-white/10 text-white"}`}>
                              <p className="text-[10px] opacity-60 mb-0.5">{msg.sender_name} • {msg.message_type}</p>
                              <p>{msg.content}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-2">
                        <Select value={messageType} onValueChange={v => setMessageType(v as MessageType)}>
                          <SelectTrigger className="border-white/10 bg-white/5 text-sm h-8"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="message">General Message</SelectItem>
                            <SelectItem value="approval">Approval / Shortlist</SelectItem>
                            <SelectItem value="interview_invite">Interview Invitation</SelectItem>
                            <SelectItem value="offer">Job Offer</SelectItem>
                            <SelectItem value="rejection">Rejection</SelectItem>
                          </SelectContent>
                        </Select>
                        <div className="flex gap-2">
                          <Textarea placeholder="Type your message…" value={newMessage} onChange={e => setNewMessage(e.target.value)}
                            className="border-white/10 bg-white/5 text-white text-sm min-h-[70px] flex-1" />
                          <Button onClick={sendMessage} disabled={sendingMsg || !newMessage.trim()}
                            className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] self-end">
                            <Send className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          {/* ── ATS Tracker ── */}
          <TabsContent value="ats">
            <div className="space-y-6">
              {/* Header row */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <BarChart2 className="h-5 w-5 text-[#8B5CF6]" /> ATS Smart Score Tracker
                  </h2>
                  <p className="text-sm text-[#94A3B8] mt-0.5">AI-powered candidate ranking based on skills, experience & keywords</p>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Select value={String(atsJobFilter)} onValueChange={v => setAtsJobFilter(!v || v === "all" ? "all" : parseInt(v))}>
                    <SelectTrigger className="border-white/10 bg-white/5 text-white text-sm w-44">
                      <SelectValue placeholder="All Jobs" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F172A] border-white/10">
                      <SelectItem value="all">All Jobs</SelectItem>
                      {jobs.map(j => <SelectItem key={j.id} value={String(j.id)}>{j.title}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/5 text-white"
                    onClick={() => setAtsSortDir(d => d === "desc" ? "asc" : "desc")}>
                    {atsSortDir === "desc" ? <ChevronDown className="mr-1 h-4 w-4" /> : <ChevronUp className="mr-1 h-4 w-4" />}
                    Score
                  </Button>
                </div>
              </div>

              {/* Score legend */}
              <div className="flex flex-wrap gap-3">
                {[{ label: "Excellent", color: "bg-green-500", range: "70–100" }, { label: "Good", color: "bg-yellow-500", range: "50–69" }, { label: "Fair", color: "bg-orange-500", range: "30–49" }, { label: "Poor", color: "bg-red-500", range: "0–29" }].map(({ label, color, range }) => (
                  <div key={label} className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                    <span className={`h-2 w-2 rounded-full ${color}`} /> {label} <span className="text-[#64748B]">({range})</span>
                  </div>
                ))}
              </div>

              {/* Per-job load buttons */}
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {jobs.filter(j => atsJobFilter === "all" || j.id === atsJobFilter).map(job => (
                  <div key={job.id} className="glass-card p-4 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium text-white text-sm truncate">{job.title}</p>
                      <p className="text-xs text-[#94A3B8]">{atsApps[job.id]?.length ?? 0} applicants scored</p>
                    </div>
                    <Button size="sm" onClick={() => loadATSForJob(job.id)}
                      disabled={atsLoading[job.id]}
                      className="bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4] shrink-0 text-xs">
                      {atsLoading[job.id]
                        ? <RefreshCw className="h-3 w-3 animate-spin" />
                        : <><RefreshCw className="mr-1 h-3 w-3" /> Compute</>}
                    </Button>
                  </div>
                ))}
              </div>

              {/* Results table */}
              {atsRows.length === 0 ? (
                <div className="glass-card p-14 text-center">
                  <BarChart2 className="mx-auto mb-4 h-12 w-12 text-[#94A3B8]" />
                  <h3 className="text-white font-semibold mb-1">No scores computed yet</h3>
                  <p className="text-sm text-[#94A3B8]">Click "Compute" on any job above to calculate ATS scores for all applicants.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {atsRows.map(({ job, app, result }, idx) => {
                    const score = result?.total ?? Math.round(app.score ?? 0);
                    const { ring, text, label } = scoreColor(score);
                    const isExpanded = expandedApp === app.id;
                    const name = app.full_name || app.candidate_info?.name || `Candidate #${app.candidate_id}`;
                    const status = STATUS_CONFIG[app.status];

                    return (
                      <div key={app.id} className="glass-card overflow-hidden">
                        {/* Row */}
                        <div className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/5 transition-colors"
                          onClick={() => setExpandedApp(isExpanded ? null : app.id)}>

                          {/* Rank */}
                          <div className="w-6 text-center text-xs font-bold text-[#64748B] shrink-0">#{idx + 1}</div>

                          {/* Score ring */}
                          <div className={`ring-2 ${ring} rounded-full shrink-0`}>
                            <ScoreRing score={score} />
                          </div>

                          {/* Candidate info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2 mb-0.5">
                              <p className="font-semibold text-white text-sm">{name}</p>
                              <Badge className={`text-[10px] border ${status.bg} ${status.color}`}>{app.status}</Badge>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-white/5 border border-white/10 ${text}`}>{label}</span>
                            </div>
                            <p className="text-xs text-[#64748B] truncate">{job.title} • {app.years_experience != null ? `${app.years_experience} yrs exp` : "exp unknown"}</p>
                          </div>

                          {/* Mini breakdown bars */}
                          {result && (
                            <div className="hidden sm:flex flex-col gap-1.5 w-44 shrink-0">
                              <div className="flex items-center gap-2 text-[10px] text-[#94A3B8]">
                                <span className="w-12 text-right shrink-0">Skills</span>
                                <div className="flex-1 h-1.5 rounded-full bg-white/10">
                                  <div className="h-full rounded-full bg-[#8B5CF6] transition-all" style={{ width: `${(result.skills_score / 60) * 100}%` }} />
                                </div>
                                <span className="w-6 text-[#8B5CF6] font-medium">{result.skills_score}</span>
                              </div>
                              <div className="flex items-center gap-2 text-[10px] text-[#94A3B8]">
                                <span className="w-12 text-right shrink-0">Exp</span>
                                <div className="flex-1 h-1.5 rounded-full bg-white/10">
                                  <div className="h-full rounded-full bg-[#06B6D4] transition-all" style={{ width: `${(result.exp_score / 20) * 100}%` }} />
                                </div>
                                <span className="w-6 text-[#06B6D4] font-medium">{result.exp_score}</span>
                              </div>
                              <div className="flex items-center gap-2 text-[10px] text-[#94A3B8]">
                                <span className="w-12 text-right shrink-0">Keywords</span>
                                <div className="flex-1 h-1.5 rounded-full bg-white/10">
                                  <div className="h-full rounded-full bg-[#F59E0B] transition-all" style={{ width: `${(result.kw_score / 20) * 100}%` }} />
                                </div>
                                <span className="w-6 text-[#F59E0B] font-medium">{result.kw_score}</span>
                              </div>
                            </div>
                          )}

                          {/* Total score badge */}
                          <div className={`shrink-0 text-right`}>
                            <div className={`text-2xl font-black ${text}`}>{score}</div>
                            <div className="text-[10px] text-[#64748B]">/ 100</div>
                          </div>

                          {/* Expand chevron */}
                          <div className={`shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`}>
                            <ChevronDown className="h-4 w-4 text-[#64748B]" />
                          </div>
                        </div>

                        {/* Expanded breakdown */}
                        {isExpanded && (
                          <div className="border-t border-white/10 p-5 grid gap-6 sm:grid-cols-2 lg:grid-cols-3 bg-white/[0.02]">
                            {/* Score breakdown */}
                            <div className="space-y-3">
                              <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">Score Breakdown</p>
                              <ScoreBar label="Skills Match" value={result?.skills_score ?? 0} max={60} color="bg-[#8B5CF6]" />
                              <ScoreBar label="Experience Match" value={result?.exp_score ?? 0} max={20} color="bg-[#06B6D4]" />
                              <ScoreBar label="Keyword Match" value={result?.kw_score ?? 0} max={20} color="bg-[#F59E0B]" />
                              <div className="pt-1 border-t border-white/10">
                                <div className="flex justify-between text-xs">
                                  <span className="text-[#64748B]">Total ATS Score</span>
                                  <span className={`font-black text-base ${text}`}>{score}/100</span>
                                </div>
                              </div>
                            </div>

                            {/* Matched skills */}
                            <div>
                              <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider mb-3">
                                Matched Skills ({result?.matched_skills.length ?? 0}/{result?.total_job_skills ?? 0})
                              </p>
                              {result && result.matched_skills.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                  {result.matched_skills.map((s, i) => (
                                    <span key={i} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/30 text-[11px] text-green-400">
                                      <CheckCircle className="h-2.5 w-2.5" /> {s}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-xs text-[#64748B]">No skill matches found</p>
                              )}
                              {result && result.total_job_skills > 0 && (
                                <div className="mt-2">
                                  {(result.total_job_skills - result.matched_skills.length) > 0 && (
                                    <p className="text-[11px] text-red-400">
                                      {result.total_job_skills - result.matched_skills.length} required skill{result.total_job_skills - result.matched_skills.length > 1 ? "s" : ""} missing
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Experience & Keywords */}
                            <div className="space-y-4">
                              <div>
                                <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider mb-2">Experience</p>
                                <div className="rounded-lg bg-white/5 border border-white/10 p-3 space-y-1.5">
                                  <div className="flex justify-between text-xs">
                                    <span className="text-[#64748B]">Candidate</span>
                                    <span className="text-white font-medium">{result?.candidate_years ?? app.years_experience ?? 0} yrs</span>
                                  </div>
                                  <div className="flex justify-between text-xs">
                                    <span className="text-[#64748B]">Required</span>
                                    <span className="text-white font-medium">{result?.required_exp ?? "Not specified"}</span>
                                  </div>
                                  <div className="flex justify-between text-xs">
                                    <span className="text-[#64748B]">Score</span>
                                    <span className={`font-bold ${(result?.exp_score ?? 0) >= 15 ? "text-green-400" : (result?.exp_score ?? 0) >= 8 ? "text-yellow-400" : "text-red-400"}`}>
                                      {result?.exp_score ?? 0}/20
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div>
                                <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider mb-2">Keywords</p>
                                <div className="rounded-lg bg-white/5 border border-white/10 p-3 space-y-1.5">
                                  <div className="flex justify-between text-xs">
                                    <span className="text-[#64748B]">Matched</span>
                                    <span className="text-white font-medium">{result?.matched_keywords ?? 0}/{result?.total_keywords ?? 0}</span>
                                  </div>
                                  <div className="flex justify-between text-xs">
                                    <span className="text-[#64748B]">Score</span>
                                    <span className={`font-bold ${(result?.kw_score ?? 0) >= 15 ? "text-green-400" : (result?.kw_score ?? 0) >= 8 ? "text-yellow-400" : "text-red-400"}`}>
                                      {result?.kw_score ?? 0}/20
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Edit Job Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <JobFormDialog title="Edit Job" form={editForm} setForm={setEditForm as any}
          onSubmit={handleEditJob} onCancel={() => setIsEditOpen(false)} />
      </Dialog>
    </div>
  );
}

// ─── Skills autocomplete input ────────────────────────────────────────────────
const ALL_SKILLS = [
  "JavaScript","TypeScript","Python","Java","C","C++","C#","Go","Rust","Ruby","PHP","Swift","Kotlin","Scala","R","MATLAB","Perl","Haskell","Lua","Dart","Elixir","Clojure","F#","Objective-C","Assembly","COBOL","Fortran","Julia","Groovy","Shell Scripting","Bash","PowerShell",
  "React","Next.js","Vue.js","Nuxt.js","Angular","Svelte","SvelteKit","HTML","CSS","Tailwind CSS","Bootstrap","SASS","LESS","Webpack","Vite","Parcel","jQuery","Alpine.js","Lit","Web Components","PWA","Storybook","Adobe XD",
  "Node.js","Express","NestJS","Fastify","Django","Flask","FastAPI","Spring Boot","Spring MVC","Laravel","Ruby on Rails","ASP.NET","ASP.NET Core",".NET","Gin","Echo","Fiber","Actix","Phoenix","Sinatra","Koa","Hapi",
  "React Native","Flutter","Android","iOS","SwiftUI","Jetpack Compose","Xamarin","Ionic","Cordova","Expo",
  "PostgreSQL","MySQL","SQLite","Microsoft SQL Server","Oracle DB","MongoDB","Redis","Cassandra","DynamoDB","Elasticsearch","CouchDB","Neo4j","InfluxDB","Firestore","Supabase","PlanetScale","MariaDB","TimescaleDB","Clickhouse",
  "AWS","GCP","Azure","Docker","Kubernetes","Terraform","Ansible","Helm","Jenkins","GitHub Actions","GitLab CI","CircleCI","Travis CI","ArgoCD","Pulumi","Serverless","Lambda","Cloud Functions","Vercel","Netlify","Heroku","Nginx","Apache","Linux","Ubuntu","Debian","RHEL",
  "Machine Learning","Deep Learning","TensorFlow","PyTorch","Keras","Scikit-learn","Pandas","NumPy","SciPy","Matplotlib","Seaborn","OpenCV","NLP","LLMs","Hugging Face","LangChain","RAG","Computer Vision","Data Engineering","Apache Spark","Apache Kafka","Apache Airflow","Hadoop","dbt","Snowflake","BigQuery","Databricks","Power BI","Tableau","Looker","Metabase","Data Analysis","Statistics","A/B Testing",
  "Cybersecurity","Penetration Testing","Ethical Hacking","Network Security","Application Security","OWASP","SOC","SIEM","Incident Response","Forensics","Cryptography","IAM","Zero Trust","Vulnerability Assessment","Burp Suite","Metasploit","Wireshark","Nmap",
  "Microservices","REST API","GraphQL","gRPC","WebSockets","Event-Driven Architecture","Domain-Driven Design","CQRS","Event Sourcing","CI/CD","Agile","Scrum","Kanban","TDD","BDD","System Design","Distributed Systems","High Availability","Load Balancing","Caching","Message Queues","RabbitMQ","MQTT",
  "UI/UX Design","Product Design","User Research","Wireframing","Prototyping","Figma","Sketch","Adobe Illustrator","Adobe Photoshop","Adobe InDesign","Motion Design","After Effects","Premiere Pro","3D Modeling","Blender","AutoCAD","Graphic Design","Brand Identity","Typography","Accessibility (a11y)",
  "Digital Marketing","SEO","SEM","Google Ads","Meta Ads","Content Marketing","Email Marketing","Marketing Automation","HubSpot","Salesforce Marketing Cloud","Social Media Marketing","Influencer Marketing","Affiliate Marketing","Copywriting","Brand Strategy","Market Research","Google Analytics","CRO","Growth Hacking","Performance Marketing",
  "Sales","B2B Sales","B2C Sales","Inside Sales","Enterprise Sales","Account Management","CRM","Salesforce","HubSpot CRM","Lead Generation","Cold Calling","Negotiation","Business Development","Partnerships","Revenue Operations","Sales Enablement",
  "Financial Analysis","Financial Modeling","Accounting","Bookkeeping","Taxation","GST","Tally","QuickBooks","SAP","Oracle Financials","Investment Banking","Equity Research","Valuation","Risk Management","Compliance","Auditing","FP&A","Cost Accounting","Payroll","Treasury",
  "Recruitment","Talent Acquisition","HR Management","HRIS","Employee Relations","Performance Management","L&D","Compensation & Benefits","Payroll Management","Onboarding","Employer Branding","Workday","BambooHR","Greenhouse","Lever",
  "Operations Management","Supply Chain Management","Logistics","Procurement","Inventory Management","Six Sigma","Lean Manufacturing","ERP","SAP ERP","Oracle ERP","Quality Assurance","Quality Control","ISO Standards","Project Management","PMP","PRINCE2","Jira","Asana","Trello","Monday.com","Confluence",
  "Legal Research","Contract Drafting","Contract Negotiation","Corporate Law","Intellectual Property","GDPR","Data Privacy","Regulatory Compliance","Employment Law","Litigation","Due Diligence","Mergers & Acquisitions",
  "Clinical Research","Pharmacovigilance","Medical Coding","Medical Writing","Healthcare Management","EMR/EHR","Radiology","Nursing","Patient Care","HIPAA","Biostatistics","Clinical Trials","Regulatory Affairs",
  "Curriculum Development","Instructional Design","e-Learning","LMS","Training & Development","Academic Research","Content Creation","Technical Writing","Documentation",
  "Customer Success","Customer Support","Technical Support","Zendesk","Freshdesk","Intercom","CSAT","NPS",
  "Communication","Leadership","Team Management","Problem Solving","Critical Thinking","Analytical Skills","Time Management","Stakeholder Management","Presentation Skills","Public Speaking","Mentoring","Cross-functional Collaboration","Strategic Planning","Decision Making",
];

function SkillsInput({ value, onChange }: { value: string[]; onChange: (skills: string[]) => void }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = query.trim().length >= 1
    ? ALL_SKILLS.filter(s => s.toLowerCase().includes(query.toLowerCase()) && !value.includes(s))
    : [];

  const addSkill = (skill: string) => {
    const trimmed = skill.trim();
    if (trimmed && !value.includes(trimmed)) onChange([...value, trimmed]);
    setQuery(""); setOpen(false); setHighlighted(0);
    inputRef.current?.focus();
  };
  const removeSkill = (skill: string) => onChange(value.filter(s => s !== skill));

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setHighlighted(h => Math.min(h + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHighlighted(h => Math.max(h - 1, 0)); }
    else if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (filtered.length > 0 && open) addSkill(filtered[highlighted]);
      else if (query.trim()) addSkill(query.replace(/,$/, "").trim());
    } else if (e.key === "Backspace" && query === "" && value.length > 0) {
      removeSkill(value[value.length - 1]);
    } else if (e.key === "Escape") { setOpen(false); }
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <div className="flex flex-wrap gap-1.5 min-h-[44px] w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 cursor-text focus-within:border-[#8B5CF6]/60 transition-colors"
        onClick={() => inputRef.current?.focus()}>
        {value.map(skill => (
          <span key={skill} className="flex items-center gap-1 rounded-md bg-[#8B5CF6]/20 border border-[#8B5CF6]/40 px-2 py-0.5 text-xs font-medium text-[#C4B5FD]">
            {skill}
            <button type="button" onClick={e => { e.stopPropagation(); removeSkill(skill); }}
              className="ml-0.5 text-[#8B5CF6] hover:text-white transition-colors leading-none text-base">×</button>
          </span>
        ))}
        <input ref={inputRef} value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); setHighlighted(0); }}
          onFocus={() => { if (query.trim()) setOpen(true); }}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? "Type a skill and press Enter…" : "Add more…"}
          className="flex-1 min-w-[140px] bg-transparent text-sm text-white placeholder:text-[#64748B] outline-none border-none py-0.5" />
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-[#0F172A] shadow-2xl overflow-hidden">
          <div ref={listRef} className="max-h-52 overflow-y-auto">
            {filtered.map((skill, i) => (
              <button key={skill} type="button"
                onMouseDown={e => { e.preventDefault(); addSkill(skill); }}
                onMouseEnter={() => setHighlighted(i)}
                className={`flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors text-left ${i === highlighted ? "bg-[#8B5CF6]/20 text-white" : "text-[#94A3B8] hover:bg-white/5 hover:text-white"}`}>
                <span className={`text-xs font-bold ${i === highlighted ? "text-[#8B5CF6]" : "text-[#475569]"}`}>+</span>
                {skill}
              </button>
            ))}
          </div>
          <div className="border-t border-white/10 px-3 py-1.5 text-[10px] text-[#475569]">
            Press <kbd className="rounded bg-white/10 px-1">Enter</kbd> to add a custom skill
          </div>
        </div>
      )}
      {open && filtered.length === 0 && query.trim().length >= 1 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-white/10 bg-[#0F172A] shadow-2xl px-3 py-2.5 text-sm text-[#94A3B8]">
          No suggestions — press <kbd className="rounded bg-white/10 px-1 text-white">Enter</kbd> to add <span className="text-white font-medium">"{query}"</span>
        </div>
      )}
    </div>
  );
}

// ─── AI Job Description Generator (no external API) ──────────────────────────
function generateJobDescription(form: any): string {
  const title: string = form.title?.trim() || "Professional";
  const location: string = form.location?.trim() || "India";
  const expLevel: string = form.experience_level?.trim() || "";
  const skills: string[] = form.skills || [];
  const empType: string = form.employment_type || "full_time";
  const salMin: number | undefined = form.salary_min;
  const salMax: number | undefined = form.salary_max;

  // Detect domain from title + skills
  const isTech = /engineer|developer|devops|architect|backend|frontend|fullstack|full.stack|software|data|ml|ai|cloud|sre|security|qa|test|mobile|android|ios/i.test(title) || skills.some(s => /javascript|python|java|react|node|aws|kubernetes|sql|typescript/i.test(s));
  const isDesign = /design|ux|ui|product design|figma|brand/i.test(title);
  const isData = /data|analyst|scientist|bi|analytics|ml|machine learning|ai/i.test(title);
  const isMarketing = /marketing|seo|sem|growth|content|brand|social/i.test(title);
  const isSales = /sales|business development|account|revenue|bd/i.test(title);
  const isFinance = /finance|accounting|auditor|analyst|cfo|controller|tax/i.test(title);
  const isHR = /hr|human resource|talent|recruiter|people/i.test(title);
  const isOps = /operations|supply chain|logistics|procurement|warehouse/i.test(title);
  const isProduct = /product manager|product owner|pm\b/i.test(title);

  // Seniority
  const isSenior = /senior|lead|principal|staff|architect|head|director|vp|chief/i.test(title + " " + expLevel);
  const isJunior = /junior|fresher|entry|trainee|intern|graduate/i.test(title + " " + expLevel);
  const seniorityLabel = isSenior ? "Senior" : isJunior ? "Junior" : "Mid-level";

  const empTypeLabel: Record<string, string> = {
    full_time: "Full-Time", part_time: "Part-Time",
    contract: "Contract", internship: "Internship", remote: "Remote",
  };
  const typeLabel = empTypeLabel[empType] || "Full-Time";

  const salaryLine = salMin && salMax
    ? `\nCompensation: ₹${(salMin / 100000).toFixed(1)}L – ₹${(salMax / 100000).toFixed(1)}L per annum`
    : salMin
    ? `\nCompensation: ₹${(salMin / 100000).toFixed(1)}L+ per annum`
    : "";

  // Domain-specific responsibilities
  const responsibilitiesMap: Record<string, string[]> = {
    tech: [
      `Design, develop, and maintain scalable ${skills.slice(0,2).join(" and ") || "software"} solutions`,
      "Write clean, well-tested, and maintainable code following best practices",
      "Collaborate with cross-functional teams including product, design, and QA",
      "Participate in code reviews and contribute to technical architecture decisions",
      "Identify and resolve performance bottlenecks and production issues",
      "Contribute to CI/CD pipelines and DevOps practices",
      "Document technical designs and maintain engineering standards",
    ],
    design: [
      "Create intuitive user interfaces and engaging user experiences",
      "Conduct user research, usability testing, and synthesize insights",
      "Develop wireframes, prototypes, and high-fidelity mockups",
      "Collaborate closely with engineers to ensure pixel-perfect implementation",
      "Define and evolve the design system and component libraries",
      "Present design concepts to stakeholders and iterate based on feedback",
    ],
    data: [
      "Collect, clean, and analyze large datasets to derive actionable insights",
      "Build dashboards, reports, and data visualizations for stakeholders",
      "Develop and maintain data pipelines and ETL workflows",
      "Apply statistical models and machine learning techniques to business problems",
      "Collaborate with product and engineering teams to instrument analytics",
      "Ensure data quality, governance, and security best practices",
    ],
    marketing: [
      "Plan and execute multi-channel digital marketing campaigns",
      "Optimize SEO/SEM strategies to drive organic and paid traffic growth",
      "Create compelling content across blogs, social media, and email channels",
      "Analyze campaign performance metrics and report on KPIs",
      "Manage brand identity and maintain consistent messaging across platforms",
      "Collaborate with sales to develop lead generation and conversion strategies",
    ],
    sales: [
      "Identify, qualify, and close new business opportunities",
      "Build and maintain strong relationships with key accounts and stakeholders",
      "Develop tailored sales pitches and presentations for prospects",
      "Meet and exceed monthly and quarterly revenue targets",
      "Collaborate with marketing on lead generation campaigns",
      "Maintain accurate pipeline data in CRM tools",
    ],
    finance: [
      "Prepare financial statements, reports, and forecasts",
      "Conduct variance analysis and provide insights to leadership",
      "Manage budgeting, cost control, and financial planning cycles",
      "Ensure regulatory compliance and coordinate with auditors",
      "Drive process improvements in financial operations",
    ],
    hr: [
      "Manage end-to-end recruitment processes for various roles",
      "Drive employee engagement, performance management, and L&D programs",
      "Handle onboarding, offboarding, and HR policy implementation",
      "Partner with business leaders on workforce planning and org design",
      "Maintain HR systems and ensure data accuracy and compliance",
    ],
    ops: [
      "Oversee day-to-day operational workflows and team performance",
      "Identify inefficiencies and implement process improvement initiatives",
      "Coordinate with vendors, suppliers, and logistics partners",
      "Monitor KPIs and prepare operational reports for leadership",
      "Ensure compliance with quality standards and regulatory requirements",
    ],
    product: [
      "Define product vision, strategy, and roadmap in collaboration with stakeholders",
      "Gather and prioritize requirements from users, customers, and business teams",
      "Write detailed product specifications and user stories",
      "Work closely with engineering and design to deliver high-quality features",
      "Analyze product metrics and user feedback to drive continuous improvements",
      "Communicate product updates and milestones to leadership and teams",
    ],
    general: [
      `Lead and execute key responsibilities within the ${title} function`,
      "Collaborate with internal teams to achieve business objectives",
      "Develop and implement strategies aligned with company goals",
      "Monitor performance metrics and report to leadership",
      "Continuously improve processes and drive operational excellence",
    ],
  };

  const domain = isTech ? "tech" : isDesign ? "design" : isData ? "data" : isMarketing ? "marketing"
    : isSales ? "sales" : isFinance ? "finance" : isHR ? "hr"
    : isOps ? "ops" : isProduct ? "product" : "general";
  const responsibilities = responsibilitiesMap[domain];

  // Requirements
  const coreRequirements: string[] = [];
  if (expLevel) coreRequirements.push(`${expLevel} of relevant experience`);
  else if (isSenior) coreRequirements.push("5+ years of relevant professional experience");
  else if (isJunior) coreRequirements.push("0–2 years of experience or strong academic background");
  else coreRequirements.push("2–5 years of relevant professional experience");

  if (skills.length > 0) {
    coreRequirements.push(`Proficiency in: ${skills.join(", ")}`);
  }

  const domainRequirements: Record<string, string[]> = {
    tech: ["Strong understanding of software design patterns and system architecture", "Experience with Agile/Scrum development methodologies", "Excellent problem-solving and debugging skills", "Familiarity with version control (Git) and code review processes"],
    design: ["Strong portfolio demonstrating UX process and visual design skills", "Proficiency in design tools such as Figma or Sketch", "Deep empathy for users and ability to translate insights into designs", "Experience working in Agile cross-functional teams"],
    data: ["Strong analytical and quantitative skills", "Experience with SQL and data visualization tools", "Ability to communicate complex findings to non-technical stakeholders", "Attention to detail and commitment to data accuracy"],
    marketing: ["Strong written and verbal communication skills", "Data-driven mindset with experience in performance analytics", "Creative thinking with ability to execute campaigns end-to-end", "Up-to-date knowledge of digital marketing trends"],
    sales: ["Proven track record of meeting or exceeding sales targets", "Excellent communication, negotiation, and relationship-building skills", "Self-motivated with a hunter mindset", "Familiarity with CRM tools"],
    finance: ["Strong knowledge of accounting principles and financial regulations", "High proficiency in Excel / financial modelling tools", "Attention to detail and ability to work under tight deadlines", "CPA, CA, or equivalent qualification preferred"],
    hr: ["Strong interpersonal and communication skills", "Knowledge of HR policies, labour laws, and best practices", "Experience with HRIS systems", "Empathy, discretion, and ability to handle sensitive situations"],
    ops: ["Strong organizational and project management skills", "Analytical mindset with ability to work with data", "Ability to manage multiple priorities in a fast-paced environment", "Experience with ERP or operations management tools"],
    product: ["Strong analytical and data-driven decision-making ability", "Excellent communication skills for cross-functional collaboration", "Experience with product lifecycle management and roadmap tools", "User-centric thinking with a passion for building great products"],
    general: ["Strong communication and interpersonal skills", "Ability to work independently and as part of a team", "Detail-oriented with excellent organizational skills", "Relevant educational qualification in the field"],
  };
  const extraReqs = domainRequirements[domain] || domainRequirements.general;

  // Perks section
  const perks = [
    "Competitive compensation and performance-linked bonuses",
    "Flexible working hours and hybrid/remote options",
    "Health insurance and wellness benefits",
    "Learning & development budget for courses and certifications",
    "Collaborative, inclusive, and growth-oriented work culture",
    "Regular team outings, events, and recognition programs",
  ];

  // Compose
  return `About the Role
We are looking for a talented and driven ${seniorityLabel} ${title} to join our growing team${location && location !== "India" ? ` in ${location}` : ""}. This is a ${typeLabel} opportunity for someone passionate about making a real impact and working in a fast-paced, collaborative environment.${salaryLine}

Key Responsibilities
${responsibilities.map(r => `• ${r}`).join("\n")}

Requirements
${[...coreRequirements, ...extraReqs].map(r => `• ${r}`).join("\n")}

What We Offer
${perks.map(p => `• ${p}`).join("\n")}

How to Apply
If you are excited about this opportunity and meet the qualifications above, we would love to hear from you. Apply now with your updated resume and a brief cover letter outlining why you are the right fit for this role.`;
}

// ─── Job form dialog ──────────────────────────────────────────────────────────
function JobFormDialog({ title, form, setForm, onSubmit, onCancel }: any) {
  const [generating, setGenerating] = useState(false);

  const handleGenerateDescription = () => {
    if (!form.title?.trim()) {
      alert("Please enter a Job Title first so the AI can generate a relevant description.");
      return;
    }
    setGenerating(true);
    // Simulate a brief "thinking" delay for UX feel
    setTimeout(() => {
      const desc = generateJobDescription(form);
      setForm((p: any) => ({ ...p, description: desc }));
      setGenerating(false);
    }, 800);
  };

  return (
    <DialogContent className="sm:max-w-[600px] bg-[#0F172A] border border-white/10 max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle className="text-white">{title}</DialogTitle>
        <DialogDescription className="text-[#94A3B8]">Fill in the job details below.</DialogDescription>
      </DialogHeader>
      <div className="grid gap-4 py-4">
        {[
          { id: "title", label: "Job Title", placeholder: "e.g. Senior React Developer" },
          { id: "location", label: "Location", placeholder: "Bengaluru / Remote" },
          { id: "experience_level", label: "Experience Level", placeholder: "e.g. 3-5 years, Senior, Junior" },
        ].map(({ id, label, placeholder }) => (
          <div key={id} className="grid gap-2">
            <Label className="text-white text-sm">{label}</Label>
            <Input value={form[id] || ""} onChange={e => setForm((p: any) => ({ ...p, [id]: e.target.value }))}
              placeholder={placeholder} className="bg-white/5 border-white/10 text-white" />
          </div>
        ))}
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <Label className="text-white text-sm">Description</Label>
            <button
              type="button"
              onClick={handleGenerateDescription}
              disabled={generating}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-[#8B5CF6]/20 to-[#06B6D4]/20 border border-[#8B5CF6]/40 px-3 py-1 text-xs font-medium text-[#C4B5FD] hover:from-[#8B5CF6]/30 hover:to-[#06B6D4]/30 hover:border-[#8B5CF6]/60 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {generating ? (
                <><RefreshCw className="h-3 w-3 animate-spin" /> Generating…</>
              ) : (
                <><Sparkles className="h-3 w-3" /> Write with AI</>
              )}
            </button>
          </div>
          <Textarea value={form.description || ""} onChange={e => setForm((p: any) => ({ ...p, description: e.target.value }))}
            placeholder="Describe the role, responsibilities, and requirements… or click ✦ Write with AI above."
            className="bg-white/5 border-white/10 text-white min-h-[160px]" />
          {form.description && (
            <p className="text-[10px] text-[#475569]">AI-generated — review and edit as needed before saving.</p>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label className="text-white text-sm">Salary Min (₹)</Label>
            <Input type="number" value={form.salary_min || ""} onChange={e => setForm((p: any) => ({ ...p, salary_min: parseInt(e.target.value) || undefined }))}
              className="bg-white/5 border-white/10 text-white" />
          </div>
          <div className="grid gap-2">
            <Label className="text-white text-sm">Salary Max (₹)</Label>
            <Input type="number" value={form.salary_max || ""} onChange={e => setForm((p: any) => ({ ...p, salary_max: parseInt(e.target.value) || undefined }))}
              className="bg-white/5 border-white/10 text-white" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label className="text-white text-sm">Employment Type</Label>
            <Select value={form.employment_type || ""} onValueChange={v => setForm((p: any) => ({ ...p, employment_type: v }))}>
              <SelectTrigger className="bg-white/5 border-white/10 text-white"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent className="bg-[#0F172A] border-white/10">
                {["full_time","part_time","contract","internship","remote"].map(t => (
                  <SelectItem key={t} value={t}>{t.replace("_"," ")}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label className="text-white text-sm">Status</Label>
            <Select value={form.status || "published"} onValueChange={v => setForm((p: any) => ({ ...p, status: v }))}>
              <SelectTrigger className="bg-white/5 border-white/10 text-white"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#0F172A] border-white/10">
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-2">
          <Label className="text-white text-sm">Skills</Label>
          <SkillsInput value={form.skills || []} onChange={skills => setForm((p: any) => ({ ...p, skills }))} />
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" className="border-white/10 text-white" onClick={onCancel}>Cancel</Button>
        <Button onClick={onSubmit} className="bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4]">Save</Button>
      </DialogFooter>
    </DialogContent>
  );
}
