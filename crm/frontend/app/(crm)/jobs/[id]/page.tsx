"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobsApi, candidatesApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { format } from "date-fns";
import {
  ArrowLeft, Briefcase, MapPin, Users, IndianRupee, TrendingUp,
  Edit2, Trash2, Clock, Tag, User,
} from "lucide-react";

const JOB_STATUSES = ["open", "on_hold", "closed", "filled"];
const STATUS_COLORS: Record<string, string> = {
  open: "badge-green", on_hold: "badge-yellow", closed: "badge-gray", filled: "badge-blue",
};
const STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"];
const STAGE_COLORS: Record<string, string> = {
  applied: "badge-gray", screening: "badge-blue", interview: "badge-purple",
  offer: "badge-yellow", hired: "badge-green", rejected: "badge-red",
};

function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function InfoRow({ label, value, icon: Icon }: { label: string; value?: string | number | null; icon?: any }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-2 py-1.5">
      {Icon && <Icon size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />}
      <span className="text-xs text-gray-500 w-32 flex-shrink-0">{label}</span>
      <span className="text-sm text-gray-800 font-medium break-all">{value}</span>
    </div>
  );
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const role = useAuthStore(s => s.user?.role);
  const canEdit = role === "owner" || role === "bdm";
  const isOwner = role === "owner";

  const [editOpen, setEditOpen] = useState(false);

  const { data: job, isLoading, error } = useQuery({
    queryKey: ["job", id],
    queryFn: () => jobsApi.get(Number(id)).then(r => r.data),
  });

  // Candidate lookup so applications can show names, not just ids
  const { data: candData } = useQuery({
    queryKey: ["candidates", "lookup"],
    queryFn: () => candidatesApi.list({ limit: 200 }).then(r => r.data),
  });
  const candMap: Record<number, any> = {};
  (candData?.data || []).forEach((c: any) => { candMap[c.id] = c; });

  const applications = job?.applications || [];

  const statusMutation = useMutation({
    mutationFn: (status: string) => jobsApi.update(Number(id), { status }),
    onSuccess: () => { toast.success("Status updated"); qc.invalidateQueries({ queryKey: ["job", id] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to update status")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => jobsApi.delete(Number(id)),
    onSuccess: () => { toast.success("Job deleted"); router.push("/jobs"); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  async function moveStage(appId: number, stage: string) {
    try {
      await jobsApi.updateStage(Number(id), appId, stage);
      toast.success("Stage updated");
      qc.invalidateQueries({ queryKey: ["job", id] });
    } catch (e: any) {
      toast.error(apiError(e, "Failed to update stage"));
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="card p-5 space-y-3">
            {[1, 2, 3].map(j => <div key={j} className="h-4 bg-gray-100 rounded animate-pulse" />)}
          </div>
        ))}
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500 mb-4">Job not found.</p>
        <button onClick={() => router.push("/jobs")} className="btn-primary">Back to Jobs</button>
      </div>
    );
  }

  const salary = job.salary_min || job.salary_max
    ? `₹${Number(job.salary_min || 0).toLocaleString("en-IN")} – ₹${Number(job.salary_max || 0).toLocaleString("en-IN")}`
    : null;
  const experience = job.experience_min != null || job.experience_max != null
    ? `${job.experience_min ?? 0} – ${job.experience_max ?? "+"} yrs`
    : null;

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/jobs")} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Briefcase size={20} className="text-brand-600" />
              {job.title}
            </h1>
            <p className="text-sm text-gray-500">{job.client_name || "—"}{job.location ? ` · ${job.location}` : ""}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${STATUS_COLORS[job.status] || "badge-gray"}`}>{job.status.replace("_", " ")}</span>
          {job.source === "portal" && <span className="badge badge-blue text-xs">From Portal</span>}
          {canEdit && (
            <button onClick={() => setEditOpen(true)} className="btn-secondary flex items-center gap-1.5 text-sm">
              <Edit2 size={14} /> Edit
            </button>
          )}
          {isOwner && (
            <button
              onClick={() => { if (confirm("Delete this job permanently?")) deleteMutation.mutate(); }}
              className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-5">
          <Section title="Job Information">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
              <InfoRow label="Title" value={job.title} icon={Briefcase} />
              <InfoRow label="Client" value={job.client_name} icon={Users} />
              <InfoRow label="Location" value={job.location} icon={MapPin} />
              <InfoRow label="Job Type" value={job.job_type} icon={Tag} />
              <InfoRow label="Experience" value={experience} icon={TrendingUp} />
              <InfoRow label="Salary" value={salary} icon={IndianRupee} />
              <InfoRow label="Positions" value={job.positions} icon={Users} />
              <InfoRow label="Deadline" value={job.deadline ? format(new Date(job.deadline), "MMM d, yyyy") : null} icon={Clock} />
            </div>
          </Section>

          {job.skills_required?.length > 0 && (
            <Section title="Skills Required">
              <div className="flex flex-wrap gap-1.5">
                {job.skills_required.map((s: string) => (
                  <span key={s} className="badge badge-purple text-xs">{s}</span>
                ))}
              </div>
            </Section>
          )}

          {job.description && (
            <Section title="Description">
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{job.description}</p>
            </Section>
          )}

          {/* Applications */}
          <Section title={`Applications (${Array.isArray(applications) ? applications.length : 0})`}>
            <div className="space-y-2">
              {!Array.isArray(applications) || applications.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No applications yet</p>
              ) : (
                applications.map((app: any) => {
                  const c = candMap[app.candidate_id];
                  return (
                    <div key={app.id} className="flex items-center justify-between gap-3 p-3 rounded-lg border border-gray-100 bg-white">
                      <button
                        onClick={() => c && router.push(`/candidates/${app.candidate_id}`)}
                        className="flex items-center gap-2 min-w-0 text-left"
                      >
                        <div className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center flex-shrink-0">
                          <User size={14} className="text-brand-600" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {c ? c.name : `Candidate #${app.candidate_id}`}
                          </p>
                          {c?.email && <p className="text-xs text-gray-500 truncate">{c.email}</p>}
                        </div>
                      </button>
                      <select
                        value={app.stage}
                        onChange={e => moveStage(app.id, e.target.value)}
                        className={`badge ${STAGE_COLORS[app.stage] || "badge-gray"} text-xs border-0 cursor-pointer`}
                      >
                        {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  );
                })
              )}
            </div>
          </Section>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <Section title="Meta">
            <InfoRow label="Source" value={job.source} icon={TrendingUp} />
            {job.portal_job_id != null && <InfoRow label="Portal ID" value={job.portal_job_id} icon={Tag} />}
            <InfoRow label="Created" value={format(new Date(job.created_at), "MMM d, yyyy")} icon={Clock} />
          </Section>

          {canEdit && (
          <Section title="Update Status">
            <div className="space-y-1.5">
              {JOB_STATUSES.map(s => (
                <button
                  key={s}
                  onClick={() => statusMutation.mutate(s)}
                  disabled={job.status === s}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm capitalize transition-colors ${
                    job.status === s
                      ? "bg-brand-600 text-white font-medium cursor-default"
                      : "hover:bg-gray-50 text-gray-600"
                  }`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </Section>
          )}
        </div>
      </div>

      {editOpen && (
        <EditJobModal
          job={job}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["job", id] });
            qc.invalidateQueries({ queryKey: ["jobs"] });
          }}
        />
      )}
    </div>
  );
}

function EditJobModal({ job, onClose, onSaved }: { job: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    title: job.title || "",
    client_name: job.client_name || "",
    location: job.location || "",
    job_type: job.job_type || "full-time",
    experience_min: job.experience_min != null ? String(job.experience_min) : "",
    experience_max: job.experience_max != null ? String(job.experience_max) : "",
    salary_min: job.salary_min != null ? String(job.salary_min) : "",
    salary_max: job.salary_max != null ? String(job.salary_max) : "",
    positions: job.positions != null ? String(job.positions) : "1",
    status: job.status || "open",
    skills_required: (job.skills_required || []).join(", "),
    description: job.description || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.title.trim()) { toast.error("Title is required"); return; }
    setSaving(true);
    try {
      await jobsApi.update(job.id, {
        ...form,
        experience_min: form.experience_min ? parseFloat(form.experience_min) : undefined,
        experience_max: form.experience_max ? parseFloat(form.experience_max) : undefined,
        salary_min: form.salary_min ? parseFloat(form.salary_min) : undefined,
        salary_max: form.salary_max ? parseFloat(form.salary_max) : undefined,
        positions: form.positions ? parseInt(form.positions) : 1,
        skills_required: form.skills_required ? form.skills_required.split(",").map((s: string) => s.trim()).filter(Boolean) : [],
      });
      toast.success("Job updated");
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(apiError(e, "Failed to save"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Edit Job</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Title *", key: "title" },
            { label: "Client Name", key: "client_name" },
            { label: "Location", key: "location" },
            { label: "Experience Min (yrs)", key: "experience_min", type: "number" },
            { label: "Experience Max (yrs)", key: "experience_max", type: "number" },
            { label: "Salary Min", key: "salary_min", type: "number" },
            { label: "Salary Max", key: "salary_max", type: "number" },
            { label: "Positions", key: "positions", type: "number" },
          ].map(field => (
            <div key={field.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{field.label}</label>
              <input
                type={field.type || "text"}
                className="input"
                value={(form as any)[field.key]}
                onChange={e => setForm({ ...form, [field.key]: e.target.value })}
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job Type</label>
            <select className="input" value={form.job_type} onChange={e => setForm({ ...form, job_type: e.target.value })}>
              {["full-time", "part-time", "contract", "internship", "remote"].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="input" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
              {JOB_STATUSES.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Skills Required (comma separated)</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. python, react, sql"
              value={form.skills_required}
              onChange={e => setForm({ ...form, skills_required: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              className="input h-24 resize-none"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : "Update Job"}
          </button>
        </div>
      </div>
    </div>
  );
}
