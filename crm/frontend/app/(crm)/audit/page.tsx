"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { Mail, RefreshCw, ShieldCheck } from "lucide-react";
import { apiError, auditApi } from "@/lib/api";

const ENTITIES = ["", "lead", "client", "candidate", "job", "application", "interview", "task", "placement", "invoice",
  "incentive", "incentive_rule", "agreement", "user", "session", "report", "email"];
const ACTIONS = ["", "create", "update", "delete", "status_change", "assign", "approve", "payment", "merge", "security",
  "login", "logout", "file_upload", "export", "email_sent", "note_added"];

function Changes({ changes }: { changes: any }) {
  if (!changes) return null;
  const entries = Object.entries(changes);
  return (
    <div className="mt-1 space-y-0.5">
      {entries.slice(0, 6).map(([k, v]: [string, any]) => (
        <p key={k} className="text-xs text-gray-500">
          <span className="font-medium text-gray-600">{k}</span>:{" "}
          {v && typeof v === "object" && "from" in v ? <>{String(v.from ?? "—")} → {String(v.to ?? "—")}</> : String(typeof v === "object" ? JSON.stringify(v) : v)}
        </p>
      ))}
      {entries.length > 6 && <p className="text-xs text-gray-400">+{entries.length - 6} more</p>}
    </div>
  );
}

function ActivityTab() {
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["audit", entity, action, page],
    queryFn: () => auditApi.logs({ entity_type: entity || undefined, action: action || undefined, page, limit: 50 }).then(r => r.data),
  });
  const rows = data?.data || [];
  const pages = data ? Math.max(1, Math.ceil(data.total / data.limit)) : 1;
  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        <select className="input w-44" value={entity} onChange={e => { setEntity(e.target.value); setPage(1); }}>
          {ENTITIES.map(x => <option key={x} value={x}>{x ? x.replace(/_/g, " ") : "All records"}</option>)}
        </select>
        <select className="input w-44" value={action} onChange={e => { setAction(e.target.value); setPage(1); }}>
          {ACTIONS.map(x => <option key={x} value={x}>{x ? x.replace(/_/g, " ") : "All actions"}</option>)}
        </select>
        <span className="text-sm text-gray-500 self-center">{data?.total ?? 0} entries</span>
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["When", "Who", "Action", "What changed", "IP"].map(h => <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400">No entries</td></tr>
              ) : rows.map((l: any) => (
                <tr key={l.id} className="border-b border-gray-50 align-top">
                  <td className="px-4 py-3 text-xs whitespace-nowrap">{format(new Date(l.created_at), "dd MMM yyyy, HH:mm")}</td>
                  <td className="px-4 py-3"><p className="text-gray-800">{l.user_name}</p><p className="text-xs text-gray-400">{l.user_email}</p></td>
                  <td className="px-4 py-3 whitespace-nowrap"><span className="badge badge-gray">{l.action.replace(/_/g, " ")}</span></td>
                  <td className="px-4 py-3 min-w-[16rem]">
                    <p className="text-gray-700">{l.description}</p>
                    <Changes changes={l.changes} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{l.ip_address || "—"}</td>
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
    </div>
  );
}

function DeliveriesTab() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("failed");
  const { data, isLoading } = useQuery({
    queryKey: ["deliveries", status],
    queryFn: () => auditApi.deliveries({ status: status || undefined, limit: 100 }).then(r => r.data),
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["deliveries"] });
  async function retry(id: number) {
    try {
      const r = await auditApi.retryDelivery(id);
      r.data.status === "sent" ? toast.success("Email sent") : toast.error(`Still failing: ${r.data.last_error || ""}`);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Retry failed"));
    }
  }
  async function retryAll() {
    try {
      const r = await auditApi.retryAllFailed();
      toast.success(`Sent ${r.data.sent} of ${r.data.attempted}`);
      refresh();
    } catch (e) {
      toast.error(apiError(e, "Retry failed"));
    }
  }
  const counts = data?.counts || {};
  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap items-center">
        {["failed", "dead", "pending", "sent", ""].map(s => (
          <button key={s} onClick={() => setStatus(s)}
                  className={`px-3 py-1.5 rounded-lg text-sm ${status === s ? "bg-brand-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}>
            {s ? `${s} (${counts[s] || 0})` : "All"}
          </button>
        ))}
        <button onClick={retryAll} className="btn-secondary text-sm flex items-center gap-1.5 ml-auto"><RefreshCw size={14} /> Retry all failed</button>
      </div>
      <p className="text-xs text-gray-500">Failed emails are retried automatically after 1 min, 5 min, 15 min, 1 h and 6 h; after that they are marked dead and can be re-sent here.</p>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left">
                {["Created", "Type", "To", "Subject", "Status", "Attempts", "Last error", ""].map(h => <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="px-4 py-8"><div className="h-8 bg-gray-100 rounded animate-pulse" /></td></tr>
              ) : (data?.data || []).length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">Nothing here</td></tr>
              ) : data.data.map((r: any) => (
                <tr key={r.id} className="border-b border-gray-50 align-top">
                  <td className="px-4 py-3 text-xs whitespace-nowrap">{r.created_at ? format(new Date(r.created_at), "dd MMM, HH:mm") : "—"}</td>
                  <td className="px-4 py-3 text-xs whitespace-nowrap">{r.category.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-xs">{r.to_email}</td>
                  <td className="px-4 py-3 text-xs min-w-[12rem]">{r.subject}</td>
                  <td className="px-4 py-3"><span className={`badge ${r.status === "sent" ? "badge-green" : r.status === "pending" ? "badge-yellow" : "badge-red"}`}>{r.status}</span></td>
                  <td className="px-4 py-3 text-xs">{r.attempts}</td>
                  <td className="px-4 py-3 text-xs text-red-600 min-w-[12rem]">{r.last_error || ""}</td>
                  <td className="px-4 py-3 text-right">{r.status !== "sent" && <button onClick={() => retry(r.id)} className="text-xs text-brand-700 hover:underline">Retry</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function AuditPage() {
  const [tab, setTab] = useState<"activity" | "emails">("activity");
  return (
    <div className="p-4 sm:p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2"><ShieldCheck size={20} className="text-brand-600" /> Audit Log</h1>
        <p className="text-sm text-gray-500">Who did what and when, with before/after values; plus every email the CRM sent.</p>
      </div>
      <div className="flex gap-1 border-b border-gray-200">
        <button onClick={() => setTab("activity")} className={`px-4 py-2 text-sm -mb-px border-b-2 ${tab === "activity" ? "border-brand-600 text-brand-700 font-medium" : "border-transparent text-gray-500"}`}>
          Activity
        </button>
        <button onClick={() => setTab("emails")} className={`px-4 py-2 text-sm -mb-px border-b-2 flex items-center gap-1.5 ${tab === "emails" ? "border-brand-600 text-brand-700 font-medium" : "border-transparent text-gray-500"}`}>
          <Mail size={14} /> Email deliveries
        </button>
      </div>
      {tab === "activity" ? <ActivityTab /> : <DeliveriesTab />}
    </div>
  );
}
