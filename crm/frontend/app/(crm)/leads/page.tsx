"use client";
import { useState, Suspense, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useSearchParams, useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Plus, Search, Filter, Trash2, Edit2, Eye, Phone, Mail, Building2, TrendingUp } from "lucide-react";
import { format } from "date-fns";

const STATUSES = ["new", "contacted", "qualified", "proposal", "negotiation", "converted", "lost"];
const TEMPS = ["hot", "warm", "cold"];
const SOURCES = ["website", "referral", "linkedin", "cold-call", "email", "event", "other"];

const STATUS_COLORS: Record<string, string> = {
  new: "badge-purple", contacted: "badge-blue", qualified: "badge-yellow",
  proposal: "badge-green", negotiation: "badge-blue", converted: "badge-green",
  lost: "badge-red",
};

const TEMP_COLORS: Record<string, string> = {
  hot: "text-red-500", warm: "text-orange-400", cold: "text-blue-400",
};

function LeadForm({ lead, onClose, onSaved }: { lead?: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    company_name: lead?.company_name || "",
    contact_name: lead?.contact_name || "",
    contact_email: lead?.contact_email || "",
    contact_phone: lead?.contact_phone || "",
    contact_designation: lead?.contact_designation || "",
    source: lead?.source || "other",
    status: lead?.status || "new",
    temperature: lead?.temperature || "cold",
    industry: lead?.industry || "",
    location: lead?.location || "",
    website: lead?.website || "",
    requirement: lead?.requirement || "",
    budget: lead?.budget || "",
    expected_positions: lead?.expected_positions || "",
    notes: lead?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const payload = { ...form, budget: form.budget ? parseFloat(form.budget) : undefined, expected_positions: form.expected_positions ? parseInt(form.expected_positions) : undefined };
      if (lead?.id) await leadsApi.update(lead.id, payload);
      else await leadsApi.create(payload);
      toast.success(lead?.id ? "Lead updated" : "Lead created");
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
          <h2 className="text-lg font-semibold">{lead?.id ? "Edit Lead" : "New Lead"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { label: "Company Name *", key: "company_name", required: true },
            { label: "Contact Name *", key: "contact_name", required: true },
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
                required={field.required}
              />
            </div>
          ))}

          {/* Selects */}
          {[
            { label: "Status", key: "status", opts: STATUSES },
            { label: "Temperature", key: "temperature", opts: TEMPS },
            { label: "Source", key: "source", opts: SOURCES },
          ].map(({ label, key, opts }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <select className="input" value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })}>
                {opts.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
              </select>
            </div>
          ))}

          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Requirement / Notes</label>
            <textarea
              className="input h-20 resize-none"
              value={form.requirement}
              onChange={e => setForm({ ...form, requirement: e.target.value })}
              placeholder="Describe the hiring requirement..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-6 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? "Saving..." : lead?.id ? "Update" : "Create Lead"}
          </button>
        </div>
      </div>
    </div>
  );
}

function LeadsContent() {
  const qc = useQueryClient();
  const role = useAuthStore(s => s.user?.role);
  const canDelete = role === "owner" || role === "bdm";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editLead, setEditLead] = useState<any>(null);
  const [page, setPage] = useState(1);
  const searchParams = useSearchParams();
  const router = useRouter();

  // Open the create-lead modal when arriving with ?new=1 (e.g. from Pipeline)
  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setEditLead(null);
      setShowForm(true);
      router.replace("/leads");
    }
  }, [searchParams, router]);

  const { data, isLoading } = useQuery({
    queryKey: ["leads", { search, status, page }],
    queryFn: () => leadsApi.list({ search, status: status || undefined, page, limit: 20 }).then(r => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => leadsApi.delete(id),
    onSuccess: () => { toast.success("Lead deleted"); qc.invalidateQueries({ queryKey: ["leads"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete")),
  });

  const leads = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Leads</h1>
          <p className="text-sm text-gray-500">{total} total leads</p>
        </div>
        <div className="flex gap-2">
          <a href="/pipeline" className="btn-secondary flex items-center gap-2"><TrendingUp size={15} /> Pipeline View</a>
          <button onClick={() => { setEditLead(null); setShowForm(true); }} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> Add Lead
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input className="input pl-9" placeholder="Search leads..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <select className="input w-40" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All Status</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Company</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Contact</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Status</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Temp</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Source</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500">Date</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-500 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-50">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : leads.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No leads found</td></tr>
              ) : leads.map((lead: any) => (
                <tr key={lead.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Building2 size={14} className="text-gray-400 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-gray-800">{lead.company_name}</p>
                        {lead.industry && <p className="text-xs text-gray-400">{lead.industry}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-700">{lead.contact_name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                      {lead.contact_email && <span className="flex items-center gap-1"><Mail size={10} />{lead.contact_email}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${STATUS_COLORS[lead.status] || "badge-gray"}`}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${TEMP_COLORS[lead.temperature] || "text-gray-400"}`}>
                      {lead.temperature === "hot" ? "🔥" : lead.temperature === "warm" ? "☀️" : "❄️"} {lead.temperature}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{lead.source || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {format(new Date(lead.created_at), "MMM d, yyyy")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <a href={`/leads/${lead.id}`} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600">
                        <Eye size={14} />
                      </a>
                      <button onClick={() => { setEditLead(lead); setShowForm(true); }} className="p-1.5 hover:bg-gray-100 rounded text-gray-500 hover:text-brand-600">
                        <Edit2 size={14} />
                      </button>
                      {canDelete && (
                        <button
                          onClick={() => { if (confirm("Delete this lead?")) deleteMutation.mutate(lead.id); }}
                          className="p-1.5 hover:bg-red-50 rounded text-gray-500 hover:text-red-500"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
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

      {/* Form modal */}
      {showForm && (
        <LeadForm
          lead={editLead}
          onClose={() => setShowForm(false)}
          onSaved={() => qc.invalidateQueries({ queryKey: ["leads"] })}
        />
      )}
    </div>
  );
}

export default function LeadsPage() {
  return <Suspense><LeadsContent /></Suspense>;
}
