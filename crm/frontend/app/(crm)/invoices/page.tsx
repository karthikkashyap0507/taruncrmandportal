"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { Download, Receipt } from "lucide-react";
import { analyticsApi, apiError, downloadReport, invoicesApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const inr = (n?: number) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const day = (d?: string | null) => (d ? format(new Date(d), "dd MMM yyyy") : "—");

export default function InvoicesPage() {
  const qc = useQueryClient();
  const isOwner = useAuthStore(s => s.user?.role === "owner");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["invoices", status, page],
    queryFn: () => invoicesApi.list({ status: status || undefined, page, limit: 25 }).then(r => r.data),
  });
  const { data: rev } = useQuery({ queryKey: ["revenue"], queryFn: () => analyticsApi.revenue().then(r => r.data) });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["invoices"] });
    qc.invalidateQueries({ queryKey: ["revenue"] });
  };

  async function markPaid(id: number) {
    if (!confirm("Mark this invoice as paid? Incentives for the credited team members will be generated.")) return;
    try {
      await invoicesApi.markPaid(id);
      toast.success("Invoice marked paid; incentives generated");
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Could not mark paid"));
    }
  }

  async function cancel(id: number) {
    const reason = prompt("Reason for cancelling this invoice (required):");
    if (!reason) return;
    try {
      await invoicesApi.cancel(id, reason);
      toast.success("Invoice cancelled; related incentives voided");
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Could not cancel"));
    }
  }

  const rows = data?.data || [];
  const pages = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 1;
  const now = Date.now();
  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Receipt size={20} className="text-brand-600" /> Invoices</h1>
          <p className="text-sm text-gray-500">Raised from joined placements; amounts follow the client&apos;s MOU (+GST)</p>
        </div>
        <button onClick={() => downloadReport("invoices").catch(e => toast.error(apiError(e)))} className="btn-secondary flex items-center gap-2">
          <Download size={15} /> Export
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[["Invoiced", rev?.invoiced], ["Collected", rev?.collected], ["Outstanding", rev?.outstanding], ["Overdue", rev?.overdue]].map(([label, v]) => (
          <div key={label as string} className="card p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-xl font-bold ${label === "Overdue" && Number(v) > 0 ? "text-red-600" : "text-gray-900"}`}>{inr(v as number)}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "sent", "paid", "cancelled"].map(s => (
          <button key={s} onClick={() => { setStatus(s); setPage(1); }}
                  className={`px-3 py-1.5 rounded-lg text-sm ${status === s ? "bg-brand-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}>
            {s === "" ? "All" : s === "sent" ? "Unpaid" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["Invoice", "Client / Candidate", "Amount", "GST", "Total", "Issued", "Due", "Status", ""].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={9} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={9} className="px-4 py-12 text-center text-gray-400">No invoices yet</td></tr>
              ) : rows.map((i: any) => {
                const overdue = i.status === "sent" && new Date(i.due_date).getTime() < now;
                return (
                  <tr key={i.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800 whitespace-nowrap">
                      {i.invoice_number}
                      {i.amount_overridden && <p className="text-xs text-orange-600" title={i.override_reason}>amount overridden</p>}
                    </td>
                    <td className="px-4 py-3"><p className="text-gray-800">{i.company_name}</p><p className="text-xs text-gray-400">{i.candidate_name}</p></td>
                    <td className="px-4 py-3 whitespace-nowrap">{inr(i.amount)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-500">{inr(i.gst_amount)}</td>
                    <td className="px-4 py-3 whitespace-nowrap font-medium">{inr(i.total_amount)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs">{day(i.issue_date)}</td>
                    <td className={`px-4 py-3 whitespace-nowrap text-xs ${overdue ? "text-red-600 font-medium" : ""}`}>{day(i.due_date)}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${i.status === "paid" ? "badge-green" : i.status === "cancelled" ? "badge-gray" : overdue ? "badge-red" : "badge-yellow"}`}>
                        {overdue ? "overdue" : i.status === "sent" ? "unpaid" : i.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap space-x-2">
                      {isOwner && i.status === "sent" && <button onClick={() => markPaid(i.id)} className="text-xs text-green-700 hover:underline">Mark paid</button>}
                      {isOwner && i.status !== "cancelled" && <button onClick={() => cancel(i.id)} className="text-xs text-red-600 hover:underline">Cancel</button>}
                    </td>
                  </tr>
                );
              })}
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
      {!isOwner && <p className="text-xs text-gray-500">Only the owner can mark invoices paid, cancel them or change an amount.</p>}
    </div>
  );
}
