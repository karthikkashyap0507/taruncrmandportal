"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clientsApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { format } from "date-fns";
import {
  ArrowLeft, Building2, Globe, MapPin, Users, Mail, Phone,
  Edit2, Trash2, Plus, Clock, Linkedin, Tag, Star,
} from "lucide-react";

const INDUSTRIES = ["IT / Software", "Finance", "Healthcare", "Manufacturing", "Retail", "Education", "Real Estate", "Consulting", "Other"];

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

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const role = useAuthStore(s => s.user?.role);
  const canEdit = role === "owner" || role === "bdm";
  const isOwner = role === "owner";

  const [editOpen, setEditOpen] = useState(false);
  const [showContactForm, setShowContactForm] = useState(false);
  const [contactForm, setContactForm] = useState({ name: "", designation: "", email: "", phone: "", linkedin_url: "" });

  const { data: client, isLoading, error } = useQuery({
    queryKey: ["client", id],
    queryFn: () => clientsApi.get(Number(id)).then(r => r.data),
  });

  const contacts = client?.contacts || [];

  const deleteMutation = useMutation({
    mutationFn: () => clientsApi.delete(Number(id)),
    onSuccess: () => { toast.success("Client deleted"); router.push("/clients"); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  async function submitContact() {
    if (!contactForm.name.trim()) { toast.error("Contact name required"); return; }
    try {
      await clientsApi.addContact(Number(id), { ...contactForm, company_id: Number(id) });
      toast.success("Contact added");
      setContactForm({ name: "", designation: "", email: "", phone: "", linkedin_url: "" });
      setShowContactForm(false);
      qc.invalidateQueries({ queryKey: ["client", id] });
    } catch (e: any) {
      toast.error(apiError(e, "Failed to add contact"));
    }
  }

  async function deleteContact(contactId: number) {
    if (!confirm("Delete this contact?")) return;
    try {
      await clientsApi.deleteContact(contactId);
      toast.success("Contact removed");
      qc.invalidateQueries({ queryKey: ["client", id] });
    } catch (e: any) {
      toast.error(apiError(e, "Failed to remove contact"));
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

  if (error || !client) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500 mb-4">Client not found.</p>
        <button onClick={() => router.push("/clients")} className="btn-primary">Back to Clients</button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/clients")} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Building2 size={20} className="text-brand-600" />
              {client.name}
            </h1>
            <p className="text-sm text-gray-500">{client.industry || "—"}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {canEdit && (
            <button onClick={() => setEditOpen(true)} className="btn-secondary flex items-center gap-1.5 text-sm">
              <Edit2 size={14} /> Edit
            </button>
          )}
          {isOwner && (
          <button
            onClick={() => { if (confirm("Delete this client permanently?")) deleteMutation.mutate(); }}
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
          <Section title="Company Information">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
              <InfoRow label="Company Name" value={client.name} icon={Building2} />
              <InfoRow label="Industry" value={client.industry} icon={Tag} />
              <InfoRow label="Location" value={client.location} icon={MapPin} />
              <InfoRow label="Company Size" value={client.size} icon={Users} />
              <InfoRow label="Website" value={client.website} icon={Globe} />
              <InfoRow label="LinkedIn" value={client.linkedin_url} icon={Linkedin} />
            </div>
            {client.description && (
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap mt-4">{client.description}</p>
            )}
          </Section>

          {/* Contacts */}
          <Section
            title={`Contacts (${Array.isArray(contacts) ? contacts.length : 0})`}
            action={canEdit ? (
              <button onClick={() => setShowContactForm(v => !v)} className="btn-secondary flex items-center gap-1.5 text-xs">
                <Plus size={13} /> Add Contact
              </button>
            ) : undefined}
          >
            {showContactForm && (
              <div className="bg-gray-50 rounded-lg p-4 space-y-3 mb-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input className="input text-sm" placeholder="Name *" value={contactForm.name} onChange={e => setContactForm(f => ({ ...f, name: e.target.value }))} />
                  <input className="input text-sm" placeholder="Designation" value={contactForm.designation} onChange={e => setContactForm(f => ({ ...f, designation: e.target.value }))} />
                  <input className="input text-sm" placeholder="Email" value={contactForm.email} onChange={e => setContactForm(f => ({ ...f, email: e.target.value }))} />
                  <input className="input text-sm" placeholder="Phone" value={contactForm.phone} onChange={e => setContactForm(f => ({ ...f, phone: e.target.value }))} />
                </div>
                <div className="flex gap-2">
                  <button onClick={submitContact} className="btn-primary text-sm">Save Contact</button>
                  <button onClick={() => setShowContactForm(false)} className="btn-secondary text-sm">Cancel</button>
                </div>
              </div>
            )}
            <div className="space-y-2">
              {!Array.isArray(contacts) || contacts.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No contacts yet</p>
              ) : (
                contacts.map((ct: any) => (
                  <div key={ct.id} className="flex items-start justify-between gap-3 p-3 rounded-lg border border-gray-100 bg-white">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800">{ct.name}</span>
                        {ct.is_primary && <span className="badge badge-green text-xs">Primary</span>}
                        {ct.designation && <span className="text-xs text-gray-500">· {ct.designation}</span>}
                      </div>
                      <div className="flex flex-wrap gap-3 mt-1">
                        {ct.email && <span className="text-xs text-gray-500 flex items-center gap-1"><Mail size={11} /> {ct.email}</span>}
                        {ct.phone && <span className="text-xs text-gray-500 flex items-center gap-1"><Phone size={11} /> {ct.phone}</span>}
                      </div>
                    </div>
                    {canEdit && (
                      <button onClick={() => deleteContact(ct.id)} className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded flex-shrink-0">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </Section>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          <Section title="Meta">
            <InfoRow label="Created" value={format(new Date(client.created_at), "MMM d, yyyy")} icon={Clock} />
          </Section>
        </div>
      </div>

      {editOpen && (
        <EditClientModal
          client={client}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ["client", id] });
            qc.invalidateQueries({ queryKey: ["clients"] });
          }}
        />
      )}
    </div>
  );
}

function EditClientModal({ client, onClose, onSaved }: { client: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: client.name || "",
    website: client.website || "",
    location: client.location || "",
    size: client.size || "",
    industry: client.industry || "",
    linkedin_url: client.linkedin_url || "",
    description: client.description || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.name.trim()) { toast.error("Company name is required"); return; }
    setSaving(true);
    try {
      await clientsApi.update(client.id, form);
      toast.success("Client updated");
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
          <h2 className="text-lg font-semibold">Edit Client</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Company Name *", key: "name" },
            { label: "Website", key: "website" },
            { label: "Location", key: "location" },
            { label: "Company Size", key: "size" },
            { label: "LinkedIn URL", key: "linkedin_url" },
          ].map(field => (
            <div key={field.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{field.label}</label>
              <input
                className="input"
                value={(form as any)[field.key]}
                onChange={e => setForm({ ...form, [field.key]: e.target.value })}
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Industry</label>
            <select className="input" value={form.industry} onChange={e => setForm({ ...form, industry: e.target.value })}>
              <option value="">Select...</option>
              {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              className="input h-20 resize-none"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : "Update Client"}
          </button>
        </div>
      </div>
    </div>
  );
}
