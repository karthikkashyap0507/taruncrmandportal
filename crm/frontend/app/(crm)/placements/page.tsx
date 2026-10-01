"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { Award, Plus, Download } from "lucide-react";
import {
  analyticsApi, apiError, candidatesApi, downloadReport, invoicesApi, jobsApi, placementsApi, usersApi,
} from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const STATUS_STYLE: Record<string, string> = {
  offered: "badge-blue", joined: "badge-green", dropped: "badge-gray", left_in_guarantee: "badge-red",
};
const inr = (n?: number) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const day = (d?: string | null) => (d ? format(new Date(d), "dd MMM yyyy") : "—");

function RecordOfferModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    candidate_id: "", job_id: "", offered_ctc: "", offer_date: "", expected_joining_date: "", bdm_id: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const { data: cands } = useQuery({
    queryKey: ["placement-cands", search],
    queryFn: () => candidatesApi.list({ search: search || undefined, limit: 50 }).then(r => r.data.data),
  });
  const { data: jobs } = useQuery({
    queryKey: ["placement-jobs"],
    queryFn: () => jobsApi.list({ limit: 200 }).then(r => r.data.data),
  });
  const { data: team } = useQuery({ queryKey: ["directory"], queryFn: () => usersApi.directory().then(r => r.data) });

  async function save() {
    if (!form.candidate_id || !form.job_id || !form.offered_ctc) {
      toast.error("Choose the candidate and job, and enter the annual CTC");
      return;
    }
    setSaving(true);
    try {
      const res = await placementsApi.create({
        candidate_id: Number(form.candidate_id),
        job_id: Number(form.job_id),
        offered_ctc: Number(form.offered_ctc),
        offer_date: form.offer_date ? new Date(form.offer_date).toISOString() : undefined,
        expected_joining_date: form.expected_joining_date ? new Date(form.expected_joining_date).toISOString() : undefined,
        bdm_id: form.bdm_id ? Number(form.bdm_id) : undefined,
        notes: form.notes || undefined,
      });
      toast.success(`Offer recorded. Fee ${inr(res.data.fee_amount)} as per the client's MOU`);
      onSaved();
      onClose();
    } catch (e) {
      toast.error(apiError(e, "Could not record the offer"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">Record an offer</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Candidate *</label>
            <input className="input mb-2" placeholder="Search by name, email or phone" value={search}
                   onChange={e => setSearch(e.target.value)} />
            <select className="input" value={form.candidate_id} onChange={e => setForm({ ...form, candidate_id: e.target.value })}>
              <option value="">Select candidate</option>
              {(cands || []).map((c: any) => <option key={c.id} value={c.id}>{c.name} {c.email ? `(${c.email})` : ""}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Job (must be linked to a client) *</label>
            <select className="input" value={form.job_id} onChange={e => setForm({ ...form, job_id: e.target.value })}>
              <option value="">Select job</option>
              {(jobs || []).map((j: any) => (
                <option key={j.id} value={j.id}>{j.title}{j.client_name ? ` - ${j.client_name}` : ""}{j.company_id ? "" : " (no client)"}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Annual CTC offered (₹) *</label>
            <input type="number" min={0} className="input" value={form.offered_ctc}
                   onChange={e => setForm({ ...form, offered_ctc: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">BDM credited</label>
            <select className="input" value={form.bdm_id} onChange={e => setForm({ ...form, bdm_id: e.target.value })}>
              <option value="">None</option>
              {(team || []).filter((u: any) => u.role === "bdm").map((u: any) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Offer date</label>
            <input type="date" className="input" value={form.offer_date} onChange={e => setForm({ ...form, offer_date: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Expected joining date</label>
            <input type="date" className="input" value={form.expected_joining_date}
                   onChange={e => setForm({ ...form, expected_joining_date: e.target.value })} />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="input h-20 resize-none" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
          <p className="sm:col-span-2 text-xs text-gray-500">
            The placement fee is calculated from the client&apos;s active MOU and frozen at this point. You&apos;ll be
            credited as the recruiter.
          </p>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Saving..." : "Record offer"}</button>
        </div>
      </div>
    </div>
  );
}

export default function PlacementsPage() {
  const qc = useQueryClient();
  const user = useAuthStore(s => s.user);
  const canBill = user?.role === "owner" || user?.role === "bdm";
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["placements", status, page],
    queryFn: () => placementsApi.list({ status: status || undefined, page, limit: 25 }).then(r => r.data),
  });
  const { data: summary } = useQuery({ queryKey: ["placements-summary"], queryFn: () => analyticsApi.placementsSummary().then(r => r.data) });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["placements"] });
    qc.invalidateQueries({ queryKey: ["placements-summary"] });
  };

  async function changeStatus(id: number, next: string, label: string) {
    if (!confirm(`Mark this placement as "${label}"?`)) return;
    try {
      await placementsApi.setStatus(id, next);
      toast.success(`Marked ${label}`);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Could not update the placement"));
    }
  }

  async function raiseInvoice(id: number) {
    if (!confirm("Raise the invoice for this placement? The amount comes from the client's MOU.")) return;
    try {
      const res = await invoicesApi.create({ placement_id: id });
      toast.success(`Invoice ${res.data.invoice_number} raised for ${inr(res.data.total_amount)}`);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Could not raise the invoice"));
    }
  }

  const rows = data?.data || [];
  const pages = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 1;

  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Award size={20} className="text-brand-600" /> Placements</h1>
          <p className="text-sm text-gray-500">Offers, joinings and replacements{user?.role === "hr" ? " credited to you" : ""}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => downloadReport("placements").catch(e => toast.error(apiError(e)))} className="btn-secondary flex items-center gap-2">
            <Download size={15} /> Export
          </button>
          <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2"><Plus size={15} /> Record offer</button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {["offered", "joined", "dropped", "left_in_guarantee"].map(s => (
          <button key={s} onClick={() => { setStatus(status === s ? "" : s); setPage(1); }}
                  className={`card p-4 text-left ${status === s ? "ring-2 ring-brand-500" : ""}`}>
            <p className="text-xs text-gray-500 capitalize">{s.replace(/_/g, " ")}</p>
            <p className="text-2xl font-bold text-gray-900">{summary?.[s] ?? 0}</p>
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["Candidate", "Client / Job", "CTC", "Fee", "Status", "Joining", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No placements yet</td></tr>
              ) : rows.map((p: any) => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{p.candidate_name}</td>
                  <td className="px-4 py-3"><p className="text-gray-800">{p.company_name}</p><p className="text-xs text-gray-400">{p.job_title}</p></td>
                  <td className="px-4 py-3 whitespace-nowrap">{inr(p.offered_ctc)}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {inr(p.fee_amount)}
                    <p className="text-xs text-gray-400">{p.fee_type === "percentage" ? `${p.fee_value}% of CTC` : "fixed fee"}</p>
                  </td>
                  <td className="px-4 py-3"><span className={`badge ${STATUS_STYLE[p.status] || "badge-gray"}`}>{p.status.replace(/_/g, " ")}</span></td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                    {p.joined_on ? `Joined ${day(p.joined_on)}` : `Expected ${day(p.expected_joining_date)}`}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap space-x-2">
                    {p.status === "offered" && (<>
                      <button onClick={() => changeStatus(p.id, "joined", "joined")} className="text-xs text-green-700 hover:underline">Joined</button>
                      <button onClick={() => changeStatus(p.id, "dropped", "did not join")} className="text-xs text-gray-500 hover:underline">Didn&apos;t join</button>
                    </>)}
                    {p.status === "joined" && (<>
                      {canBill && <button onClick={() => raiseInvoice(p.id)} className="text-xs text-brand-700 hover:underline">Raise invoice</button>}
                      <button onClick={() => changeStatus(p.id, "left_in_guarantee", "left within guarantee")} className="text-xs text-red-600 hover:underline">Left in guarantee</button>
                    </>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {pages > 1 && (
        <div className="flex justify-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary text-sm">Previous</button>
          <span className="text-sm text-gray-500 self-center">Page {page} of {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="btn-secondary text-sm">Next</button>
        </div>
      )}

      {showForm && <RecordOfferModal onClose={() => setShowForm(false)} onSaved={refresh} />}
    </div>
  );
}
