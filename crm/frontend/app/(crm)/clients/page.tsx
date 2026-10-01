"use client";
import { useState } from "react";
import { useAuthStore } from "@/store/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clientsApi, apiError } from "@/lib/api";
import toast from "react-hot-toast";
import { Plus, Search, Building2, Globe, MapPin, Trash2, Eye, Edit2 } from "lucide-react";

const INDUSTRIES = ["IT", "Finance", "Healthcare", "Manufacturing", "Retail", "Education", "Other"];

function ClientForm({ client, onClose, onSaved }: { client?: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: client?.name || "", industry: client?.industry || "",
    website: client?.website || "", location: client?.location || "",
    size: client?.size || "", description: client?.description || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.name.trim()) return toast.error("Company name required");
    setSaving(true);
    try {
      if (client?.id) await clientsApi.update(client.id, form);
      else await clientsApi.create(form);
      toast.success(client?.id ? "Client updated" : "Client created");
      onSaved(); onClose();
    } catch (e: any) { toast.error(apiError(e, "Failed")); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">{client?.id ? "Edit Client" : "Add Client"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Company Name *", key: "name" },
            { label: "Website", key: "website" },
            { label: "Location", key: "location" },
            { label: "Company Size", key: "size", placeholder: "e.g. 50-200" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
              <input className="input" value={(form as any)[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })} placeholder={(f as any).placeholder} />
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
            <textarea className="input h-16 resize-none" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Saving..." : client?.id ? "Update" : "Add Client"}</button>
        </div>
      </div>
    </div>
  );
}

export default function ClientsPage() {
  const role = useAuthStore(s => s.user?.role);
  const canEdit = role === "owner" || role === "bdm";
  const isOwner = role === "owner";
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editClient, setEditClient] = useState<any>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["clients", { search, page }],
    queryFn: () => clientsApi.list({ search, page, limit: 20 }).then(r => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => clientsApi.delete(id),
    onSuccess: () => { toast.success("Client deleted"); qc.invalidateQueries({ queryKey: ["clients"] }); },
  });

  const clients = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div><h1 className="text-xl font-bold text-gray-900">Clients</h1><p className="text-sm text-gray-500">{total} clients</p></div>
        {canEdit && (
          <button onClick={() => { setEditClient(null); setShowForm(true); }} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> Add Client
          </button>
        )}
      </div>

      <div className="relative max-w-sm">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input className="input pl-9" placeholder="Search clients..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.length === 0 && (
            <div className="col-span-3 card p-12 text-center text-gray-400">
              <Building2 size={32} className="mx-auto mb-3 text-gray-300" />
              No clients yet
            </div>
          )}
          {clients.map((c: any) => (
            <div key={c.id} className="card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Building2 size={18} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 leading-tight">{c.name}</p>
                    {c.industry && <p className="text-xs text-gray-400">{c.industry}</p>}
                  </div>
                </div>
              </div>
              {c.website && (
                <a href={c.website} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs text-blue-500 hover:underline mb-1">
                  <Globe size={11} />{c.website.replace(/https?:\/\//, "")}
                </a>
              )}
              {c.location && (
                <p className="flex items-center gap-1.5 text-xs text-gray-400 mb-1"><MapPin size={11} />{c.location}</p>
              )}
              {c.size && <p className="text-xs text-gray-400">Size: {c.size}</p>}
              <div className="flex items-center gap-1 mt-4 pt-3 border-t border-gray-50">
                <a href={`/clients/${c.id}`} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600"><Eye size={14} /></a>
                {canEdit && <button onClick={() => { setEditClient(c); setShowForm(true); }} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600"><Edit2 size={14} /></button>}
                {isOwner && <button onClick={() => { if (confirm("Delete client?")) deleteMutation.mutate(c.id); }} className="p-1.5 hover:bg-red-50 rounded text-gray-500 hover:text-red-500"><Trash2 size={14} /></button>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && <ClientForm client={editClient} onClose={() => setShowForm(false)} onSaved={() => qc.invalidateQueries({ queryKey: ["clients"] })} />}
    </div>
  );
}
