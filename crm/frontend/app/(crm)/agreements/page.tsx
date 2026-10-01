"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { FileText, Plus, Upload } from "lucide-react";
import { agreementsApi, apiError, clientsApi, fileUrl } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const STATUS_STYLE: Record<string, string> = {
  draft: "badge-gray", active: "badge-green", expired: "badge-yellow", terminated: "badge-red",
};
const day = (d?: string | null) => (d ? format(new Date(d), "dd MMM yyyy") : "—");

function AgreementModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    company_id: "", title: "", fee_type: "percentage", fee_value: "", payment_terms_days: "30",
    replacement_guarantee_days: "90", start_date: "", end_date: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const { data: clients } = useQuery({
    queryKey: ["clients-all"],
    queryFn: () => clientsApi.list({ limit: 200 }).then(r => r.data.data),
  });

  async function save() {
    if (!form.company_id || !form.title || !form.fee_value || !form.start_date) {
      toast.error("Client, title, fee and start date are required");
      return;
    }
    setSaving(true);
    try {
      await agreementsApi.create({
        company_id: Number(form.company_id),
        title: form.title,
        fee_type: form.fee_type,
        fee_value: Number(form.fee_value),
        payment_terms_days: Number(form.payment_terms_days || 30),
        replacement_guarantee_days: Number(form.replacement_guarantee_days || 90),
        start_date: new Date(form.start_date).toISOString(),
        end_date: form.end_date ? new Date(form.end_date).toISOString() : undefined,
        notes: form.notes || undefined,
      });
      toast.success("MOU saved as a draft. The owner activates it.");
      onSaved();
      onClose();
    } catch (e) {
      toast.error(apiError(e, "Could not save the MOU"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">New MOU</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Client *</label>
            <select className="input" value={form.company_id} onChange={e => setForm({ ...form, company_id: e.target.value })}>
              <option value="">Select client</option>
              {(clients || []).map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
            <input className="input" placeholder="e.g. Master Services Agreement 2026" value={form.title}
                   onChange={e => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Fee type</label>
            <select className="input" value={form.fee_type} onChange={e => setForm({ ...form, fee_type: e.target.value })}>
              <option value="percentage">% of annual CTC</option>
              <option value="fixed">Fixed fee per placement</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{form.fee_type === "percentage" ? "Fee (%) *" : "Fee (₹) *"}</label>
            <input type="number" min={0} className="input" value={form.fee_value} onChange={e => setForm({ ...form, fee_value: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Payment terms (days)</label>
            <input type="number" min={0} className="input" value={form.payment_terms_days}
                   onChange={e => setForm({ ...form, payment_terms_days: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Replacement guarantee (days)</label>
            <input type="number" min={0} className="input" value={form.replacement_guarantee_days}
                   onChange={e => setForm({ ...form, replacement_guarantee_days: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Start date *</label>
            <input type="date" className="input" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End date</label>
            <input type="date" className="input" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="input h-20 resize-none" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Saving..." : "Save draft"}</button>
        </div>
      </div>
    </div>
  );
}

export default function AgreementsPage() {
  const qc = useQueryClient();
  const user = useAuthStore(s => s.user);
  const isOwner = user?.role === "owner";
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["agreements"],
    queryFn: () => agreementsApi.list({ limit: 200 }).then(r => r.data),
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["agreements"] });

  async function setStatus(id: number, status: string) {
    if (!confirm(`Set this MOU to "${status}"?`)) return;
    try {
      await agreementsApi.setStatus(id, status);
      toast.success(`MOU ${status}`);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Could not change the MOU status"));
    }
  }

  async function upload(id: number, file?: File) {
    if (!file) return;
    try {
      await agreementsApi.uploadDocument(id, file);
      toast.success("Signed copy uploaded");
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Upload failed"));
    }
  }

  const rows = data?.data || [];
  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2"><FileText size={20} className="text-brand-600" /> MOUs</h1>
          <p className="text-sm text-gray-500">Client fee agreements. Placements and invoices are billed on the active MOU.</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2"><Plus size={15} /> New MOU</button>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["Client", "MOU", "Fee", "Terms", "Period", "Status", "Signed copy", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">No MOUs yet</td></tr>
              ) : rows.map((a: any) => (
                <tr key={a.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{a.company_name}</td>
                  <td className="px-4 py-3 text-gray-700">{a.title}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {a.fee_type === "percentage" ? `${a.fee_value}% of CTC` : `₹${Number(a.fee_value).toLocaleString("en-IN")}`}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">
                    Pay in {a.payment_terms_days} days<br />Guarantee {a.replacement_guarantee_days} days
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">{day(a.start_date)} → {a.end_date ? day(a.end_date) : "open"}</td>
                  <td className="px-4 py-3"><span className={`badge ${STATUS_STYLE[a.status] || "badge-gray"}`}>{a.status}</span></td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {a.document_url && <a href={fileUrl(a.document_url)} target="_blank" rel="noreferrer" className="text-xs text-brand-700 hover:underline mr-2">View</a>}
                    <label className="text-xs text-gray-500 hover:text-brand-700 cursor-pointer inline-flex items-center gap-1">
                      <Upload size={12} /> Upload
                      <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={e => upload(a.id, e.target.files?.[0])} />
                    </label>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap space-x-2">
                    {isOwner && a.status === "draft" && <button onClick={() => setStatus(a.id, "active")} className="text-xs text-green-700 hover:underline">Activate</button>}
                    {isOwner && a.status === "active" && <button onClick={() => setStatus(a.id, "terminated")} className="text-xs text-red-600 hover:underline">Terminate</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {!isOwner && <p className="text-xs text-gray-500">Only the owner can activate an MOU or change the terms of an active one.</p>}
      {showForm && <AgreementModal onClose={() => setShowForm(false)} onSaved={refresh} />}
    </div>
  );
}
