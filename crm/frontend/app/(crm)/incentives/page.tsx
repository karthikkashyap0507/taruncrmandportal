"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { Download, Wallet } from "lucide-react";
import { apiError, downloadReport, incentivesApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const inr = (n?: number) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const STATUS_STYLE: Record<string, string> = { pending: "badge-yellow", approved: "badge-blue", paid: "badge-green", void: "badge-gray" };

function RulesPanel({ isOwner }: { isOwner: boolean }) {
  const qc = useQueryClient();
  const { data: rules } = useQuery({ queryKey: ["incentive-rules"], queryFn: () => incentivesApi.rules().then(r => r.data) });
  const [draft, setDraft] = useState<Record<string, string>>({});
  useEffect(() => {
    if (rules) setDraft(Object.fromEntries(rules.map((r: any) => [r.role, String(r.percentage)])));
  }, [rules]);

  async function save(role: string) {
    try {
      await incentivesApi.updateRule(role, Number(draft[role]));
      toast.success(`Rate for ${role.toUpperCase()} saved. It applies to invoices paid from now on.`);
      qc.invalidateQueries({ queryKey: ["incentive-rules"] });
    } catch (e) {
      toast.error(apiError(e, "Could not save the rate"));
    }
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Incentive rates</h3>
      <p className="text-xs text-gray-500 mb-4">% of the invoice amount (before GST), paid to the credited recruiter and BDM when an invoice is paid.</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {(rules || []).map((r: any) => (
          <div key={r.role} className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700 w-14 uppercase">{r.role}</span>
            {isOwner ? (<>
              <input type="number" min={0} max={50} step={0.5} className="input w-24" value={draft[r.role] ?? ""}
                     onChange={e => setDraft({ ...draft, [r.role]: e.target.value })} />
              <span className="text-sm text-gray-500">%</span>
              <button onClick={() => save(r.role)} className="btn-secondary text-xs">Save</button>
            </>) : <span className="text-sm text-gray-800">{r.percentage}%</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function IncentivesPage() {
  const qc = useQueryClient();
  const user = useAuthStore(s => s.user);
  const isOwner = user?.role === "owner";
  const [status, setStatus] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["incentives", status],
    queryFn: () => incentivesApi.list({ status: status || undefined, limit: 200 }).then(r => r.data),
  });
  const { data: summary } = useQuery({ queryKey: ["incentive-summary"], queryFn: () => incentivesApi.summary().then(r => r.data) });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["incentives"] });
    qc.invalidateQueries({ queryKey: ["incentive-summary"] });
  };

  async function act(fn: () => Promise<unknown>, done: string) {
    try {
      await fn();
      toast.success(done);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Action failed"));
    }
  }

  const rows = data?.data || [];
  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Wallet size={20} className="text-brand-600" /> Incentives</h1>
          <p className="text-sm text-gray-500">{isOwner ? "Payouts for the whole team" : "Your payouts"}. Generated automatically when an invoice is paid.</p>
        </div>
        <button onClick={() => downloadReport("incentives").catch(e => toast.error(apiError(e)))} className="btn-secondary flex items-center gap-2">
          <Download size={15} /> Export
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {["pending", "approved", "paid", "void"].map(s => (
          <button key={s} onClick={() => setStatus(status === s ? "" : s)} className={`card p-4 text-left ${status === s ? "ring-2 ring-brand-500" : ""}`}>
            <p className="text-xs text-gray-500 capitalize">{s}</p>
            <p className="text-xl font-bold text-gray-900">{inr(summary?.[s]?.amount)}</p>
            <p className="text-xs text-gray-400">{summary?.[s]?.count ?? 0} payout(s)</p>
          </button>
        ))}
      </div>

      <RulesPanel isOwner={isOwner} />

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["Person", "Invoice", "Basis", "Rate", "Amount", "Status", "Date", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">No incentives yet</td></tr>
              ) : rows.map((i: any) => (
                <tr key={i.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3"><p className="font-medium text-gray-800">{i.user_name}</p><p className="text-xs text-gray-400 uppercase">{i.role}</p></td>
                  <td className="px-4 py-3 whitespace-nowrap">{i.invoice_number}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{inr(i.basis_amount)}</td>
                  <td className="px-4 py-3">{i.rate}%</td>
                  <td className="px-4 py-3 whitespace-nowrap font-medium">{inr(i.amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${STATUS_STYLE[i.status] || "badge-gray"}`} title={i.void_reason || ""}>{i.status}</span>
                  </td>
                  <td className="px-4 py-3 text-xs whitespace-nowrap">{i.created_at ? format(new Date(i.created_at), "dd MMM yyyy") : "—"}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap space-x-2">
                    {isOwner && i.status === "pending" && <button onClick={() => act(() => incentivesApi.approve(i.id), "Approved")} className="text-xs text-blue-700 hover:underline">Approve</button>}
                    {isOwner && i.status === "approved" && <button onClick={() => act(() => incentivesApi.markPaid(i.id), "Marked paid")} className="text-xs text-green-700 hover:underline">Mark paid</button>}
                    {isOwner && (i.status === "pending" || i.status === "approved") && (
                      <button onClick={() => { const r = prompt("Reason for voiding:"); if (r) act(() => incentivesApi.void(i.id, r), "Voided"); }}
                              className="text-xs text-red-600 hover:underline">Void</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
