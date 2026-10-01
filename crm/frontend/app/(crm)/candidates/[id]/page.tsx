"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { candidatesApi, apiError, fileUrl } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { format } from "date-fns";
import {
  ArrowLeft, User, Mail, Phone, MapPin, Briefcase, Building2,
  Edit2, Trash2, MessageSquare, Clock, Star, IndianRupee,
  Linkedin, FileText, TrendingUp, Tag,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "badge-gray", screening: "badge-blue", shortlisted: "badge-yellow",
  interviewing: "badge-purple", offered: "badge-green", placed: "badge-green", rejected: "badge-red",
};
const STATUSES = ["new", "screening", "shortlisted", "interviewing", "offered", "placed", "rejected"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{title}</h3>
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

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const isOwner = useAuthStore(s => s.user?.role === "owner");

  const [editOpen, setEditOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ["candidate", id],
    queryFn: () => candidatesApi.get(Number(id)).then(r => r.data),
  });

  const notes = candidate?.candidate_notes || [];

  const statusMutation = useMutation({
    mutationFn: (status: string) => candidatesApi.update(Number(id), { status }),
    onSuccess: () => { toast.success("Status updated"); qc.invalidateQueries({ queryKey: ["candidate", id] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to update status")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => candidatesApi.delete(Number(id)),
    onSuccess: () => { toast.success("Candidate deleted"); router.push("/candidates"); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  async function submitNote() {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      await candidatesApi.addNote(Number(id), noteText.trim());
      setNoteText("");
      toast.success("Note added");
      qc.invalidateQueries({ queryKey: ["candidate", id] });
    } catch (e: any) {
      toast.error(apiError(e, "Failed to add note"));
    } finally {
      setAddingNote(false);
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

  if (error || !candidate) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500 mb-4">Candidate not found.</p>
        <button onClick={() => router.push("/candidates")} className="btn-primary">Back to Candidates</button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/candidates")} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <User size={20} className="text-brand-600" />
              {candidate.name}
            </h1>
            <p className="text-sm text-gray-500">
              {candidate.current_title || "—"}{candidate.current_company ? ` · ${candidate.current_company}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${STATUS_COLORS[candidate.status] || "badge-gray"}`}>{candidate.status}</span>
          {candidate.ats_score != null && (
            <span className="text-sm font-medium text-yellow-500 flex items-center gap-1">
              <Star size={14} /> {candidate.ats_score}
            </span>
          )}
          {candidate.source === "portal" && <span className="badge badge-blue text-xs">From Portal</span>}
          <button onClick={() => setEditOpen(true)} className="btn-secondary flex items-center gap-1.5 text-sm">
            <Edit2 size={14} /> Edit
          </button>
          {isOwner && (
            <button
              onClick={() => { if (confirm("Delete this candidate permanently?")) deleteMutation.mutate(); }}
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

          <Section title="Candidate Information">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
              <InfoRow label="Full Name" value={candidate.name} icon={User} />
              <InfoRow label="Email" value={candidate.email} icon={Mail} />
              <InfoRow label="Phone" value={candidate.phone} icon={Phone} />
              <InfoRow label="Location" value={candidate.location} icon={MapPin} />
              <InfoRow label="Current Title" value={candidate.current_title} icon={Briefcase} />
              <InfoRow label="Current Company" value={candidate.current_company} icon={Building2} />
              <InfoRow label="Experience" value={candidate.experience_years != null ? `${candidate.experience_years} yrs` : null} icon={TrendingUp} />
              <InfoRow label="Expected Salary" value={candidate.expected_salary} icon={IndianRupee} />
              <InfoRow label="Notice Period" value={candidate.notice_period} icon={Clock} />
              <InfoRow label="LinkedIn" value={candidate.linkedin_url} icon={Linkedin} />
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              {candidate.resume_url && (
                <a
                  href={fileUrl(candidate.resume_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary inline-flex items-center gap-2 text-sm"
                >
                  <FileText size={14} /> View Resume
                </a>
              )}
              <label className="btn-secondary inline-flex items-center gap-2 text-sm cursor-pointer">
                <FileText size={14} /> {candidate.resume_url ? "Replace resume" : "Upload resume"}
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  className="hidden"
                  onChange={async e => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    try {
                      await candidatesApi.uploadResume(Number(id), file);
                      toast.success("Resume uploaded");
                      qc.invalidateQueries({ queryKey: ["candidate", id] });
                    } catch (err: any) {
                      toast.error(apiError(err, "Upload failed"));
                    }
                  }}
                />
              </label>
            </div>
          </Section>

          {candidate.skills?.length > 0 && (
            <Section title="Skills">
              <div className="flex flex-wrap gap-1.5">
                {candidate.skills.map((s: string) => (
                  <span key={s} className="badge badge-purple text-xs">{s}</span>
                ))}
              </div>
            </Section>
          )}

          {/* Notes */}
          <Section title={`Notes (${Array.isArray(notes) ? notes.length : 0})`}>
            <div className="space-y-3 mb-4 max-h-72 overflow-y-auto">
              {!Array.isArray(notes) || notes.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No notes yet</p>
              ) : (
                notes.map((note: any) => (
                  <div key={note.id} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{note.content}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {format(new Date(note.created_at), "MMM d, yyyy · h:mm a")}
                    </p>
                  </div>
                ))
              )}
            </div>
            <div className="flex gap-2">
              <textarea
                className="input flex-1 h-16 resize-none text-sm"
                placeholder="Add a note..."
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) submitNote(); }}
              />
              <button
                onClick={submitNote}
                disabled={addingNote || !noteText.trim()}
                className="btn-primary px-4 self-end"
              >
                <MessageSquare size={15} />
              </button>
            </div>
          </Section>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <Section title="Meta">
            <InfoRow label="Source" value={candidate.source} icon={TrendingUp} />
            {candidate.portal_candidate_id != null && (
              <InfoRow label="Portal ID" value={candidate.portal_candidate_id} icon={Tag} />
            )}
            <InfoRow label="Created" value={format(new Date(candidate.created_at), "MMM d, yyyy")} icon={Clock} />
            {candidate.updated_at && (
              <InfoRow label="Updated" value={format(new Date(candidate.updated_at), "MMM d, yyyy")} icon={Clock} />
            )}
            {candidate.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {candidate.tags.map((tag: string) => (
                  <span key={tag} className="badge badge-gray text-xs">{tag}</span>
                ))}
              </div>
            )}
          </Section>

          <Section title="Update Status">
            <div className="space-y-1.5">
              {STATUSES.map(s => (
                <button
                  key={s}
                  onClick={() => statusMutation.mutate(s)}
                  disabled={candidate.status === s}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    candidate.status === s
                      ? "bg-brand-600 text-white font-medium cursor-default"
                      : "hover:bg-gray-50 text-gray-600"
                  }`}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </Section>
        </div>
      </div>

      {editOpen && (
        <EditCandidateModal
          candidate={candidate}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["candidate", id] });
            qc.invalidateQueries({ queryKey: ["candidates"] });
          }}
        />
      )}
    </div>
  );
}

function EditCandidateModal({ candidate, onClose, onSaved }: { candidate: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: candidate.name || "",
    email: candidate.email || "",
    phone: candidate.phone || "",
    current_title: candidate.current_title || "",
    current_company: candidate.current_company || "",
    location: candidate.location || "",
    experience_years: candidate.experience_years != null ? String(candidate.experience_years) : "",
    expected_salary: candidate.expected_salary || "",
    notice_period: candidate.notice_period || "",
    linkedin_url: candidate.linkedin_url || "",
    status: candidate.status || "new",
    skills: (candidate.skills || []).join(", "),
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.name.trim()) { toast.error("Name is required"); return; }
    setSaving(true);
    try {
      await candidatesApi.update(candidate.id, {
        ...form,
        experience_years: form.experience_years ? parseFloat(form.experience_years) : undefined,
        skills: form.skills ? form.skills.split(",").map((s: string) => s.trim()).filter(Boolean) : [],
      });
      toast.success("Candidate updated");
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
          <h2 className="text-lg font-semibold">Edit Candidate</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Name *", key: "name" },
            { label: "Email", key: "email", type: "email" },
            { label: "Phone", key: "phone" },
            { label: "Current Title", key: "current_title" },
            { label: "Current Company", key: "current_company" },
            { label: "Location", key: "location" },
            { label: "Experience (years)", key: "experience_years", type: "number" },
            { label: "Expected Salary", key: "expected_salary" },
            { label: "Notice Period", key: "notice_period" },
            { label: "LinkedIn URL", key: "linkedin_url" },
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
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="input" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
              {STATUSES.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Skills (comma separated)</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. python, react, sql"
              value={form.skills}
              onChange={e => setForm({ ...form, skills: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : "Update Candidate"}
          </button>
        </div>
      </div>
    </div>
  );
}
