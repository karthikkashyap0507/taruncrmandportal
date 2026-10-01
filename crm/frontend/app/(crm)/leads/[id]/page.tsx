"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { format } from "date-fns";
import {
  ArrowLeft, Building2, Mail, Phone, Globe, MapPin, Briefcase,
  Edit2, Trash2, Plus, CheckCircle2, Clock, MessageSquare,
  TrendingUp, IndianRupee, Users, Tag,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "badge-purple", contacted: "badge-blue", qualified: "badge-yellow",
  proposal: "badge-green", negotiation: "badge-blue", converted: "badge-green", lost: "badge-red",
};
const TEMP_COLORS: Record<string, string> = {
  hot: "text-red-500", warm: "text-orange-400", cold: "text-blue-400",
};
const STATUSES = ["new", "contacted", "qualified", "proposal", "negotiation", "converted", "lost"];
const FOLLOWUP_TYPES = ["call", "email", "meeting", "whatsapp", "other"];

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

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const role = useAuthStore(s => s.user?.role);
  const canDelete = role === "owner" || role === "bdm";

  const [editOpen, setEditOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [showFollowupForm, setShowFollowupForm] = useState(false);
  const [followupForm, setFollowupForm] = useState({ scheduled_at: "", type: "call", notes: "" });

  const { data: lead, isLoading, error } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => leadsApi.get(Number(id)).then(r => r.data),
  });

  const { data: notes = [] } = useQuery({
    queryKey: ["lead-notes", id],
    queryFn: () => leadsApi.getNotes(Number(id)).then(r => r.data),
    enabled: !!id,
  });

  const { data: followups = [] } = useQuery({
    queryKey: ["lead-followups", id],
    queryFn: () => leadsApi.getFollowups(Number(id)).then(r => r.data),
    enabled: !!id,
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => leadsApi.updateStatus(Number(id), status),
    onSuccess: () => { toast.success("Status updated"); qc.invalidateQueries({ queryKey: ["lead", id] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to update status")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => leadsApi.delete(Number(id)),
    onSuccess: () => { toast.success("Lead deleted"); router.push("/leads"); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  async function submitNote() {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      await leadsApi.addNote(Number(id), noteText.trim());
      setNoteText("");
      toast.success("Note added");
      qc.invalidateQueries({ queryKey: ["lead-notes", id] });
    } catch {
      toast.error("Failed to add note");
    } finally {
      setAddingNote(false);
    }
  }

  async function submitFollowup() {
    if (!followupForm.scheduled_at) { toast.error("Select date/time"); return; }
    try {
      await leadsApi.addFollowup(Number(id), {
        scheduled_at: new Date(followupForm.scheduled_at).toISOString(),
        type: followupForm.type,
        notes: followupForm.notes || undefined,
      });
      toast.success("Follow-up scheduled");
      setFollowupForm({ scheduled_at: "", type: "call", notes: "" });
      setShowFollowupForm(false);
      qc.invalidateQueries({ queryKey: ["lead-followups", id] });
    } catch {
      toast.error("Failed to schedule follow-up");
    }
  }

  async function completeFollowup(fupId: number) {
    try {
      await leadsApi.completeFollowup(Number(id), fupId);
      toast.success("Marked complete");
      qc.invalidateQueries({ queryKey: ["lead-followups", id] });
    } catch {
      toast.error("Failed");
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

  if (error || !lead) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500 mb-4">Lead not found.</p>
        <button onClick={() => router.push("/leads")} className="btn-primary">Back to Leads</button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/leads")} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Building2 size={20} className="text-brand-600" />
              {lead.company_name}
            </h1>
            <p className="text-sm text-gray-500">
              {lead.contact_name}{lead.contact_designation ? ` · ${lead.contact_designation}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${STATUS_COLORS[lead.status] || "badge-gray"}`}>{lead.status}</span>
          <span className={`text-sm font-medium ${TEMP_COLORS[lead.temperature] || "text-gray-400"}`}>
            {lead.temperature === "hot" ? "🔥" : lead.temperature === "warm" ? "☀️" : "❄️"} {lead.temperature}
          </span>
          <button onClick={() => setEditOpen(true)} className="btn-secondary flex items-center gap-1.5 text-sm">
            <Edit2 size={14} /> Edit
          </button>
          {canDelete && (
            <button
              onClick={() => { if (confirm("Delete this lead permanently?")) deleteMutation.mutate(); }}
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

          {/* Contact & Company Info */}
          <Section title="Contact Information">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
              <InfoRow label="Contact Name" value={lead.contact_name} icon={Users} />
              <InfoRow label="Designation" value={lead.contact_designation} icon={Briefcase} />
              <InfoRow label="Email" value={lead.contact_email} icon={Mail} />
              <InfoRow label="Phone" value={lead.contact_phone} icon={Phone} />
              <InfoRow label="Company" value={lead.company_name} icon={Building2} />
              <InfoRow label="Industry" value={lead.industry} icon={Tag} />
              <InfoRow label="Location" value={lead.location} icon={MapPin} />
              <InfoRow label="Website" value={lead.website} icon={Globe} />
            </div>
          </Section>

          {/* Requirement */}
          {lead.requirement && (
            <Section title="Requirement">
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{lead.requirement}</p>
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

          {/* Follow-ups */}
          <Section title={`Follow-ups (${Array.isArray(followups) ? followups.length : 0})`}>
            <div className="space-y-2 mb-4">
              {!Array.isArray(followups) || followups.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No follow-ups scheduled</p>
              ) : (
                followups.map((fup: any) => (
                  <div key={fup.id} className={`flex items-start gap-3 p-3 rounded-lg border ${fup.completed ? "bg-green-50 border-green-100" : "bg-white border-gray-100"}`}>
                    <button
                      onClick={() => !fup.completed && completeFollowup(fup.id)}
                      className={fup.completed ? "text-green-500 cursor-default mt-0.5" : "text-gray-300 hover:text-green-500 mt-0.5"}
                    >
                      <CheckCircle2 size={16} />
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-gray-600 capitalize">{fup.type}</span>
                        {fup.completed && <span className="badge badge-green text-xs">Done</span>}
                      </div>
                      <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                        <Clock size={11} />
                        {format(new Date(fup.scheduled_at), "MMM d, yyyy · h:mm a")}
                      </p>
                      {fup.notes && <p className="text-xs text-gray-600 mt-1">{fup.notes}</p>}
                    </div>
                  </div>
                ))
              )}
            </div>

            {showFollowupForm ? (
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Date & Time</label>
                    <input
                      type="datetime-local"
                      className="input text-sm"
                      value={followupForm.scheduled_at}
                      onChange={e => setFollowupForm(f => ({ ...f, scheduled_at: e.target.value }))}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                    <select
                      className="input text-sm"
                      value={followupForm.type}
                      onChange={e => setFollowupForm(f => ({ ...f, type: e.target.value }))}
                    >
                      {FOLLOWUP_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
                  <input
                    type="text"
                    className="input text-sm"
                    placeholder="e.g. Discuss proposal pricing"
                    value={followupForm.notes}
                    onChange={e => setFollowupForm(f => ({ ...f, notes: e.target.value }))}
                  />
                </div>
                <div className="flex gap-2">
                  <button onClick={submitFollowup} className="btn-primary text-sm">Schedule</button>
                  <button onClick={() => setShowFollowupForm(false)} className="btn-secondary text-sm">Cancel</button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowFollowupForm(true)}
                className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
              >
                <Plus size={14} /> Schedule Follow-up
              </button>
            )}
          </Section>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Deal Details */}
          <Section title="Deal Details">
            <InfoRow label="Source" value={lead.source} icon={TrendingUp} />
            {lead.budget && (
              <InfoRow label="Budget" value={`₹${Number(lead.budget).toLocaleString("en-IN")}`} icon={IndianRupee} />
            )}
            <InfoRow label="Positions" value={lead.expected_positions} icon={Users} />
            <InfoRow label="Created" value={format(new Date(lead.created_at), "MMM d, yyyy")} icon={Clock} />
            {lead.updated_at && (
              <InfoRow label="Updated" value={format(new Date(lead.updated_at), "MMM d, yyyy")} icon={Clock} />
            )}
            {lead.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {lead.tags.map((tag: string) => (
                  <span key={tag} className="badge badge-gray text-xs">{tag}</span>
                ))}
              </div>
            )}
          </Section>

          {/* Update Status */}
          <Section title="Update Status">
            <div className="space-y-1.5">
              {STATUSES.map(s => (
                <button
                  key={s}
                  onClick={() => statusMutation.mutate(s)}
                  disabled={lead.status === s}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    lead.status === s
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

      {/* Edit Modal */}
      {editOpen && (
        <EditLeadModal
          lead={lead}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["lead", id] });
            qc.invalidateQueries({ queryKey: ["leads"] });
          }}
        />
      )}
    </div>
  );
}

function EditLeadModal({ lead, onClose, onSaved }: { lead: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    company_name: lead.company_name || "",
    contact_name: lead.contact_name || "",
    contact_email: lead.contact_email || "",
    contact_phone: lead.contact_phone || "",
    contact_designation: lead.contact_designation || "",
    source: lead.source || "other",
    status: lead.status || "new",
    temperature: lead.temperature || "cold",
    industry: lead.industry || "",
    location: lead.location || "",
    website: lead.website || "",
    requirement: lead.requirement || "",
    budget: lead.budget ? String(lead.budget) : "",
    expected_positions: lead.expected_positions ? String(lead.expected_positions) : "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await leadsApi.update(lead.id, {
        ...form,
        budget: form.budget ? parseFloat(form.budget) : undefined,
        expected_positions: form.expected_positions ? parseInt(form.expected_positions) : undefined,
      });
      toast.success("Lead updated");
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
          <h2 className="text-lg font-semibold">Edit Lead</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Company Name *", key: "company_name" },
            { label: "Contact Name *", key: "contact_name" },
            { label: "Contact Email", key: "contact_email", type: "email" },
            { label: "Contact Phone", key: "contact_phone" },
            { label: "Designation", key: "contact_designation" },
            { label: "Industry", key: "industry" },
            { label: "Location", key: "location" },
            { label: "Website", key: "website" },
            { label: "Budget (INR)", key: "budget", type: "number" },
            { label: "Expected Positions", key: "expected_positions", type: "number" },
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
          {[
            { label: "Status", key: "status", opts: ["new","contacted","qualified","proposal","negotiation","converted","lost"] },
            { label: "Temperature", key: "temperature", opts: ["hot","warm","cold"] },
            { label: "Source", key: "source", opts: ["website","referral","linkedin","cold-call","email","event","other"] },
          ].map(({ label, key, opts }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <select className="input" value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}>
                {opts.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
              </select>
            </div>
          ))}
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Requirement</label>
            <textarea
              className="input h-20 resize-none"
              value={form.requirement}
              onChange={e => setForm({ ...form, requirement: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : "Update Lead"}
          </button>
        </div>
      </div>
    </div>
  );
}
