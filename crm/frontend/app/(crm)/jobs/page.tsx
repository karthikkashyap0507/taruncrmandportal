"use client";
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { useAuthStore } from "@/store/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobsApi, portalApi, apiError } from "@/lib/api";
import { EDUCATION_OPTIONS, formatPlace } from "@/lib/format";
import toast from "react-hot-toast";
import { Plus, Search, Briefcase, MapPin, Users, Trash2, Eye, Edit2, RefreshCw, Globe } from "lucide-react";
import { format } from "date-fns";

const JOB_STATUSES = ["open", "on_hold", "closed", "filled"];
const STATUS_COLORS: Record<string, string> = {
  open: "badge-green", on_hold: "badge-yellow", closed: "badge-gray", filled: "badge-blue",
};

function JobForm({ job, onClose, onSaved }: { job?: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    title: job?.title || "", client_name: job?.client_name || "",
    location: job?.location || "", locality: job?.locality || "", education: job?.education || "",
    salary_period: job?.salary_period || "month", job_type: job?.job_type || "full-time",
    experience_min: job?.experience_min || "", experience_max: job?.experience_max || "",
    salary_min: job?.salary_min || "", salary_max: job?.salary_max || "",
    positions: job?.positions || 1, status: job?.status || "open",
    description: job?.description || "", skills_required: job?.skills_required?.join(", ") || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.title.trim()) return toast.error("Job title required");
    setSaving(true);
    try {
      const payload = {
        ...form,
        skills_required: form.skills_required.split(",").map((s: string) => s.trim()).filter(Boolean),
        experience_min: form.experience_min ? parseFloat(form.experience_min) : undefined,
        experience_max: form.experience_max ? parseFloat(form.experience_max) : undefined,
        salary_min: form.salary_min ? parseFloat(form.salary_min) : undefined,
        salary_max: form.salary_max ? parseFloat(form.salary_max) : undefined,
        positions: parseInt(form.positions),
        education: form.education || undefined,
        locality: form.locality || undefined,
      };
      if (job?.id) await jobsApi.update(job.id, payload);
      else await jobsApi.create(payload);
      toast.success(job?.id ? "Job updated" : "Job created");
      onSaved(); onClose();
    } catch (e: any) { toast.error(apiError(e, "Failed")); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">{job?.id ? "Edit Job" : "Post New Job"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Job Title *</label>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          </div>
          {[
            { label: "Client / Company", key: "client_name" },
            { label: "Location", key: "location" },
            { label: "Min Experience (yrs)", key: "experience_min", type: "number" },
            { label: "Max Experience (yrs)", key: "experience_max", type: "number" },
            { label: "Min Salary (INR)", key: "salary_min", type: "number" },
            { label: "Max Salary (INR)", key: "salary_max", type: "number" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
              <input type={f.type || "text"} className="input" value={(form as any)[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Locality / Area</label>
            <input className="input" value={form.locality} onChange={e => setForm({ ...form, locality: e.target.value })} placeholder="e.g. JP Nagar" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Minimum Education</label>
            <select className="input" value={form.education} onChange={e => setForm({ ...form, education: e.target.value })}>
              <option value="">Not specified</option>
              {EDUCATION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Salary is per</label>
            <select className="input" value={form.salary_period} onChange={e => setForm({ ...form, salary_period: e.target.value })}>
              <option value="month">Month</option>
              <option value="year">Year</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job Type</label>
            <select className="input" value={form.job_type} onChange={e => setForm({ ...form, job_type: e.target.value })}>
              {["full-time", "part-time", "contract", "internship", "freelance"].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Openings</label>
            <input type="number" min={1} className="input" value={form.positions} onChange={e => setForm({ ...form, positions: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="input" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
              {JOB_STATUSES.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Required Skills (comma separated)</label>
            <input className="input" value={form.skills_required} onChange={e => setForm({ ...form, skills_required: e.target.value })} placeholder="React, Node.js, SQL..." />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Job Description</label>
            <textarea className="input h-28 resize-none" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Saving..." : job?.id ? "Update" : "Post Job"}</button>
        </div>
      </div>
    </div>
  );
}

export default function JobsPage() {
  const role = useAuthStore(s => s.user?.role);
  const canEdit = role === "owner" || role === "bdm";
  const isOwner = role === "owner";
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editJob, setEditJob] = useState<any>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["crm-jobs", { search, status, page }],
    queryFn: () => jobsApi.list({ search, status: status || undefined, page, limit: 20 }).then(r => r.data),
  });

  const { data: sync, refetch: refetchSync } = useQuery({
    queryKey: ["portal-sync"],
    queryFn: () => portalApi.status().then(r => r.data),
    refetchInterval: 60_000,
  });
  const syncMutation = useMutation({
    mutationFn: () => portalApi.sync().then(r => r.data),
    onSuccess: (r: any) => {
      const n = (r.jobs_created || 0) + (r.applications_created || 0);
      toast.success(n ? `Synced: ${r.jobs_created} new job(s), ${r.applications_created} new applicant(s)` : "Up to date with the job portal");
      qc.invalidateQueries({ queryKey: ["crm-jobs"] });
      refetchSync();
    },
    onError: (e: any) => { toast.error(apiError(e, "Sync failed")); refetchSync(); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => jobsApi.delete(id),
    onSuccess: () => { toast.success("Job deleted"); qc.invalidateQueries({ queryKey: ["crm-jobs"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  const jobs = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-bold text-gray-900">Jobs</h1><p className="text-sm text-gray-500">{total} jobs</p></div>
        {canEdit && (
          <button onClick={() => { setEditJob(null); setShowForm(true); }} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> Post Job
          </button>
        )}
      </div>

      {sync && (
        <div className={`flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border px-4 py-2.5 text-sm ${
          !sync.configured ? "border-amber-200 bg-amber-50 text-amber-800"
            : sync.last_error ? "border-red-200 bg-red-50 text-red-700" : "border-gray-200 bg-white text-gray-600"}`}>
          <Globe size={15} className="flex-shrink-0" />
          {!sync.configured ? (
            <span>Job portal sync isn&apos;t set up on the server yet (missing integration key).</span>
          ) : (
            <span>
              Job portal: {sync.synced_jobs} job{sync.synced_jobs !== 1 ? "s" : ""} synced ({sync.open_portal_jobs} open)
              {" · "}
              {sync.last_success_at ? `last synced ${formatDistanceToNow(new Date(sync.last_success_at + (String(sync.last_success_at).endsWith("Z") || String(sync.last_success_at).includes("+") ? "" : "Z")), { addSuffix: true })}` : "not synced yet"}
              {" · syncs every "}{Math.round((sync.interval_seconds || 120) / 60)} min
              {sync.last_error && <span className="block text-xs">Last attempt failed: {sync.last_error}</span>}
            </span>
          )}
          {canEdit && sync.configured && (
            <button onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}
              className="ml-auto btn-secondary flex items-center gap-1.5 text-xs">
              <RefreshCw size={13} className={syncMutation.isPending ? "animate-spin" : ""} /> {syncMutation.isPending ? "Syncing…" : "Sync now"}
            </button>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input className="input pl-9" placeholder="Search jobs..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <select className="input w-36" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All Status</option>
          {JOB_STATUSES.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-44 bg-gray-100 rounded-xl animate-pulse" />)
        ) : jobs.length === 0 ? (
          <div className="col-span-3 card p-12 text-center text-gray-400">
            <Briefcase size={32} className="mx-auto mb-3 text-gray-300" />No jobs found
          </div>
        ) : jobs.map((j: any) => (
          <div key={j.id} className="card p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-semibold text-gray-900">{j.title}</p>
                {j.client_name && <p className="text-xs text-gray-500 mt-0.5">{j.client_name}</p>}
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className={`badge ${STATUS_COLORS[j.status] || "badge-gray"}`}>{j.status.replace("_", " ")}</span>
                {j.source === "portal" && <span className="badge badge-blue text-[10px]">Portal</span>}
              </div>
            </div>
            {j.portal_status === "pending" && (
              <p className="mb-2 text-xs text-amber-600">Waiting for admin approval on the job portal</p>
            )}
            <div className="space-y-1.5 mb-3">
              {(j.location || j.locality) && <p className="flex items-center gap-1.5 text-xs text-gray-500"><MapPin size={11} />{formatPlace(j.location, j.locality)}</p>}
              <p className="flex items-center gap-1.5 text-xs text-gray-500"><Users size={11} />{j.positions} opening{j.positions !== 1 ? "s" : ""}</p>
              {(j.experience_min || j.experience_max) && (
                <p className="text-xs text-gray-500">{j.experience_min || 0}–{j.experience_max || "∞"} yrs exp</p>
              )}
            </div>
            <div className="flex flex-wrap gap-1 mb-3">
              {(j.skills_required || []).slice(0, 4).map((s: string) => (
                <span key={s} className="badge badge-purple">{s}</span>
              ))}
            </div>
            <div className="flex items-center gap-1 pt-2 border-t border-gray-50">
              <a href={`/jobs/${j.id}`} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600"><Eye size={14} /></a>
              {canEdit && <button onClick={() => { setEditJob(j); setShowForm(true); }} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600"><Edit2 size={14} /></button>}
              {isOwner && <button onClick={() => { if (confirm("Delete job?")) deleteMutation.mutate(j.id); }} className="p-1.5 hover:bg-red-50 rounded text-gray-500 hover:text-red-500"><Trash2 size={14} /></button>}
              <span className="ml-auto text-xs text-gray-400">{format(new Date(j.created_at), "MMM d")}</span>
            </div>
          </div>
        ))}
      </div>

      {showForm && <JobForm job={editJob} onClose={() => setShowForm(false)} onSaved={() => qc.invalidateQueries({ queryKey: ["crm-jobs"] })} />}
    </div>
  );
}
