"use client";
import { useState, Suspense } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { candidatesApi } from "@/lib/api";
import toast from "react-hot-toast";
import { Plus, Search, Trash2, Edit2, Eye, Upload, Star } from "lucide-react";
import { format } from "date-fns";

const STATUSES = ["new", "screening", "shortlisted", "interviewing", "offered", "placed", "rejected"];
const SOURCES = ["portal", "linkedin", "referral", "walk-in", "job-fair", "other"];

const STATUS_COLORS: Record<string, string> = {
  new: "badge-gray", screening: "badge-blue", shortlisted: "badge-yellow",
  interviewing: "badge-purple", offered: "badge-green", placed: "badge-green", rejected: "badge-red",
};

function CandidateForm({ candidate, onClose, onSaved }: { candidate?: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: candidate?.name || "",
    email: candidate?.email || "",
    phone: candidate?.phone || "",
    current_title: candidate?.current_title || "",
    current_company: candidate?.current_company || "",
    experience_years: candidate?.experience_years || "",
    location: candidate?.location || "",
    expected_salary: candidate?.expected_salary || "",
    notice_period: candidate?.notice_period || "",
    linkedin_url: candidate?.linkedin_url || "",
    status: candidate?.status || "new",
    source: candidate?.source || "other",
    skills: candidate?.skills?.join(", ") || "",
    notes: candidate?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const payload = {
        ...form,
        skills: form.skills.split(",").map((s: string) => s.trim()).filter(Boolean),
        experience_years: form.experience_years ? parseFloat(form.experience_years) : undefined,
      };
      if (candidate?.id) await candidatesApi.update(candidate.id, payload);
      else await candidatesApi.create(payload);
      toast.success(candidate?.id ? "Candidate updated" : "Candidate added");
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">{candidate?.id ? "Edit Candidate" : "Add Candidate"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-2 gap-4">
          {[
            { label: "Full Name *", key: "name", required: true },
            { label: "Email", key: "email", type: "email" },
            { label: "Phone", key: "phone" },
            { label: "Current Title", key: "current_title" },
            { label: "Current Company", key: "current_company" },
            { label: "Experience (years)", key: "experience_years", type: "number" },
            { label: "Location", key: "location" },
            { label: "Expected Salary", key: "expected_salary" },
            { label: "Notice Period", key: "notice_period" },
            { label: "LinkedIn URL", key: "linkedin_url" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
              <input type={f.type || "text"} className="input" value={(form as any)[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
            </div>
          ))}
          {[
            { label: "Status", key: "status", opts: STATUSES },
            { label: "Source", key: "source", opts: SOURCES },
          ].map(({ label, key, opts }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <select className="input" value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}>
                {opts.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
              </select>
            </div>
          ))}
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Skills (comma separated)</label>
            <input className="input" value={form.skills} onChange={e => setForm({ ...form, skills: e.target.value })} placeholder="React, Node.js, Python..." />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="input h-20 resize-none" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : candidate?.id ? "Update" : "Add Candidate"}
          </button>
        </div>
      </div>
    </div>
  );
}

function CandidatesContent() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editCandidate, setEditCandidate] = useState<any>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["candidates", { search, status, page }],
    queryFn: () => candidatesApi.list({ search, status: status || undefined, page, limit: 20 }).then(r => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => candidatesApi.delete(id),
    onSuccess: () => { toast.success("Candidate removed"); qc.invalidateQueries({ queryKey: ["candidates"] }); },
  });

  const candidates = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Candidates</h1>
          <p className="text-sm text-gray-500">{total} total candidates</p>
        </div>
        <button onClick={() => { setEditCandidate(null); setShowForm(true); }} className="btn-primary flex items-center gap-2">
          <Plus size={15} /> Add Candidate
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input className="input pl-9" placeholder="Search candidates..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <select className="input w-44" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All Status</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Candidate</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Current Role</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Skills</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Status</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">ATS</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Added</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}><td colSpan={7} className="px-4 py-3"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
                ))
              ) : candidates.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No candidates found</td></tr>
              ) : candidates.map((c: any) => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                        <span className="text-brand-700 text-xs font-semibold">{c.name[0]}</span>
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{c.name}</p>
                        <p className="text-xs text-gray-400">{c.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-gray-700">{c.current_title || "—"}</p>
                    <p className="text-xs text-gray-400">{c.current_company}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(c.skills || []).slice(0, 3).map((s: string) => (
                        <span key={s} className="badge badge-purple text-xs">{s}</span>
                      ))}
                      {c.skills?.length > 3 && <span className="text-xs text-gray-400">+{c.skills.length - 3}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${STATUS_COLORS[c.status] || "badge-gray"}`}>{c.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {c.ats_score != null ? (
                      <div className="flex items-center gap-1.5">
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${c.ats_score >= 80 ? "bg-green-500" : c.ats_score >= 60 ? "bg-yellow-400" : "bg-red-400"}`}
                            style={{ width: `${c.ats_score}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium">{c.ats_score}</span>
                      </div>
                    ) : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">{format(new Date(c.created_at), "MMM d, yy")}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <a href={`/candidates/${c.id}`} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600">
                        <Eye size={14} />
                      </a>
                      <button onClick={() => { setEditCandidate(c); setShowForm(true); }} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600">
                        <Edit2 size={14} />
                      </button>
                      <button onClick={() => { if (confirm("Remove candidate?")) deleteMutation.mutate(c.id); }} className="p-1.5 hover:bg-red-50 rounded text-gray-500 hover:text-red-500">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 20 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">Page {page} of {Math.ceil(total / 20)}</p>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40">Prev</button>
              <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)} className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40">Next</button>
            </div>
          </div>
        )}
      </div>

      {showForm && (
        <CandidateForm
          candidate={editCandidate}
          onClose={() => setShowForm(false)}
          onSaved={() => qc.invalidateQueries({ queryKey: ["candidates"] })}
        />
      )}
    </div>
  );
}

export default function CandidatesPage() {
  return <Suspense><CandidatesContent /></Suspense>;
}
