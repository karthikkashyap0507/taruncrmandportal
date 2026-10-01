"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Briefcase, Building2, FileText, Inbox, LogOut, Mail, Newspaper, Plus, RefreshCw, Send, Shield, Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { adminApi, apiError } from "@/services/api";
import { educationLabel, formatPlace, formatSalary } from "@/lib/format";
import { useAuthStore } from "@/store/auth-store";

type Row = Record<string, any>;  // eslint-disable-line @typescript-eslint/no-explicit-any

const when = (d?: string | null) => (d ? new Date(d).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—");

function Table({ head, children, empty }: { head: string[]; children: React.ReactNode; empty: boolean }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs text-[#94A3B8]">
              {head.map(h => <th key={h} className="px-4 py-3 font-medium whitespace-nowrap">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {empty ? <tr><td colSpan={head.length} className="px-4 py-10 text-center text-[#64748B]">Nothing to show</td></tr> : children}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function useLoader<T>(fn: () => Promise<{ data: T }>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    fn().then(r => { setData(r.data); setError(null); }).catch(e => setError(apiError(e, "Could not load")));
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  return { data, error, reload: load };
}

async function act(fn: () => Promise<unknown>, reload: () => void, confirmText?: string) {
  if (confirmText && !confirm(confirmText)) return;
  try {
    await fn();
    reload();
  } catch (e) {
    alert(apiError(e, "Action failed"));
  }
}

function Overview() {
  const { data, error } = useLoader<Row>(() => adminApi.getStats(), []);
  const cards: [string, string][] = [
    ["Users", "total_users"], ["Candidates", "total_candidates"], ["Recruiters", "total_recruiters"],
    ["Companies", "total_companies"], ["Jobs", "total_jobs"], ["Published jobs", "published_jobs"],
    ["Jobs awaiting approval", "pending_jobs"],
    ["Applications", "total_applications"], ["Failed emails", "failed_emails"],
    ["New enquiries", "new_enquiries"], ["Job-alert subscribers", "newsletter_subscribers"],
  ];
  const alerting = (key: string) => (key === "failed_emails" || key === "new_enquiries" || key === "pending_jobs") && data?.[key];
  if (error) return <p className="text-red-400">{error}</p>;
  return (
    <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
      {cards.map(([label, key]) => (
        <div key={key} className="glass-card p-5">
          <p className="text-xs text-[#94A3B8]">{label}</p>
          <p className={`mt-1 text-2xl font-bold ${alerting(key) ? (key === "failed_emails" ? "text-red-400" : "text-yellow-400") : "text-white"}`}>
            {data ? data[key] ?? 0 : "…"}
          </p>
        </div>
      ))}
    </div>
  );
}

function UsersTab() {
  const [role, setRole] = useState("");
  const [page, setPage] = useState(0);
  const { data, reload } = useLoader<Row[]>(
    () => adminApi.listUsers({ role: role || undefined, include_inactive: true, skip: page * 50, limit: 50 }), [role, page]);
  const rows = data || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {["", "candidate", "recruiter", "company_admin", "platform_admin"].map(r => (
          <button key={r} onClick={() => { setRole(r); setPage(0); }}
                  className={`rounded-lg px-3 py-1.5 text-xs ${role === r ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {r ? r.replace("_", " ") : "All"}
          </button>
        ))}
      </div>
      <Table head={["Name", "Email", "Role", "Joined", "Status", ""]} empty={rows.length === 0}>
        {rows.map(u => {
          const locked = u.locked_until && new Date(u.locked_until).getTime() > Date.now();
          return (
            <tr key={u.id} className="border-b border-white/5">
              <td className="px-4 py-3 text-white">{u.name}</td>
              <td className="px-4 py-3 text-[#94A3B8]">{u.email}</td>
              <td className="px-4 py-3 text-[#94A3B8] whitespace-nowrap">{u.role.replace("_", " ")}</td>
              <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(u.created_at)}</td>
              <td className="px-4 py-3 text-xs whitespace-nowrap">
                {u.is_active === false ? <span className="text-red-400">Deactivated</span> : locked ? <span className="text-yellow-400">Locked</span> : <span className="text-green-400">Active</span>}
              </td>
              <td className="px-4 py-3 text-right whitespace-nowrap space-x-3 text-xs">
                {locked && <button onClick={() => act(() => adminApi.unlockUser(u.id), reload)} className="text-yellow-300 hover:underline">Unlock</button>}
                {u.is_active === false
                  ? <button onClick={() => act(() => adminApi.activateUser(u.id), reload)} className="text-green-300 hover:underline">Reactivate</button>
                  : u.id !== undefined && <button onClick={() => act(() => adminApi.deleteUser(u.id), reload, `Deactivate ${u.email}? They will be signed out and their jobs closed.`)} className="text-red-300 hover:underline">Deactivate</button>}
              </td>
            </tr>
          );
        })}
      </Table>
      <div className="flex justify-center gap-2">
        <Button variant="outline" className="border-white/10" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
        <Button variant="outline" className="border-white/10" disabled={rows.length < 50} onClick={() => setPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

function CompaniesTab() {
  const { data, reload } = useLoader<Row[]>(() => adminApi.listCompanies({ limit: 200 }), []);
  const rows = data || [];
  return (
    <Table head={["Company", "Industry", "Website", "Jobs", ""]} empty={rows.length === 0}>
      {rows.map(c => (
        <tr key={c.id} className="border-b border-white/5">
          <td className="px-4 py-3 text-white">{c.name}</td>
          <td className="px-4 py-3 text-[#94A3B8]">{c.industry || "—"}</td>
          <td className="px-4 py-3 text-[#94A3B8]">{c.website || "—"}</td>
          <td className="px-4 py-3 text-[#94A3B8]">{c.job_count}</td>
          <td className="px-4 py-3 text-right text-xs">
            <button onClick={() => act(() => adminApi.deleteCompany(c.id), reload,
              `Delete ${c.name}? Its jobs are removed and its recruiters deactivated.`)} className="text-red-300 hover:underline">Delete</button>
          </td>
        </tr>
      ))}
    </Table>
  );
}

const JOB_STATUS_LABEL: Record<string, string> = {
  pending: "Awaiting approval", published: "Live", rejected: "Rejected", draft: "Draft", closed: "Closed",
};

function JobsTab() {
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<number | null>(null);
  const { data, reload } = useLoader<Row[]>(
    () => adminApi.listJobs({ status: status || undefined, skip: page * 50, limit: 50 }), [status, page]);
  const rows = data || [];
  const reject = async (j: Row) => {
    const reason = prompt(`Why is "${j.title}" being rejected? The poster sees this and can fix the job.`);
    if (reason === null) return;
    if (reason.trim().length < 3) { alert("Please give a short reason (at least 3 characters)."); return; }
    await act(() => adminApi.rejectJob(j.id, reason.trim()), reload);
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {[["pending", "Awaiting approval"], ["published", "Live"], ["rejected", "Rejected"], ["draft", "Draft"], ["closed", "Closed"], ["", "All"]].map(([s, label]) => (
          <button key={s} onClick={() => { setStatus(s); setPage(0); }}
                  className={`rounded-lg px-3 py-1.5 text-xs ${status === s ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {label}
          </button>
        ))}
        <Link href="/dashboard/recruiter" className="ml-auto">
          <Button variant="outline" className="border-white/10"><Plus className="mr-2 h-4 w-4" /> Post a job</Button>
        </Link>
      </div>
      <p className="text-xs text-[#64748B]">Jobs posted by recruiters and freelancers stay hidden from candidates until you approve them. Click a row to read the full job.</p>
      <Table head={["Job", "Posted by", "Location", "Pay", "Status", ""]} empty={rows.length === 0}>
        {rows.map(j => (
          <Fragment key={j.id}>
            <tr onClick={() => setOpen(open === j.id ? null : j.id)} className="cursor-pointer border-b border-white/5 align-top hover:bg-white/5">
              <td className="px-4 py-3">
                <div className="text-white">{j.title}</div>
                <div className="text-xs text-[#94A3B8]">{j.company_name || `Company #${j.company_id}`}</div>
              </td>
              <td className="px-4 py-3 text-xs">
                <div className="text-white">{j.posted_by || "—"}</div>
                <div className="text-[#94A3B8]">{j.posted_by_email || ""}</div>
              </td>
              <td className="px-4 py-3 text-xs text-[#94A3B8]">{formatPlace(j.location, j.locality) || "—"}</td>
              <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{formatSalary(j.salary_min, j.salary_max, j.salary_period)}</td>
              <td className={`px-4 py-3 text-xs whitespace-nowrap ${j.status === "pending" ? "text-yellow-400" : j.status === "published" ? "text-green-400" : j.status === "rejected" ? "text-red-400" : "text-[#94A3B8]"}`}>
                {JOB_STATUS_LABEL[j.status] || j.status}
              </td>
              <td className="px-4 py-3 text-right text-xs space-x-3 whitespace-nowrap" onClick={ev => ev.stopPropagation()}>
                {j.status !== "published" && (
                  <button onClick={() => act(() => adminApi.approveJob(j.id), reload)} className="text-green-300 hover:underline">
                    {j.status === "pending" || j.status === "rejected" ? "Approve" : "Publish"}
                  </button>
                )}
                {(j.status === "pending" || j.status === "published") && (
                  <button onClick={() => reject(j)} className="text-red-300 hover:underline">Reject</button>
                )}
                {j.status === "published" && (
                  <button onClick={() => act(() => adminApi.updateJobStatus(j.id, "closed"), reload)} className="text-[#3B82F6] hover:underline">Close</button>
                )}
              </td>
            </tr>
            {open === j.id && (
              <tr className="border-b border-white/5">
                <td colSpan={6} className="px-4 pb-4 text-sm text-[#CBD5E1]">
                  <div className="mb-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#94A3B8]">
                    <span>Qualification: {educationLabel(j.education) || "Not stated"}</span>
                    <span>Experience: {j.experience_level || "Not stated"}</span>
                    <span>Type: {j.employment_type?.replace("_", " ") || "Not stated"}</span>
                    <span>Posted: {when(j.created_at)}</span>
                  </div>
                  {j.review_note && <p className="mb-2 text-xs text-red-300">Rejection reason: {j.review_note}</p>}
                  <p className="whitespace-pre-wrap break-words">{j.description}</p>
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </Table>
      <div className="flex justify-center gap-2">
        <Button variant="outline" className="border-white/10" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
        <Button variant="outline" className="border-white/10" disabled={rows.length < 50} onClick={() => setPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

function AuditTab() {
  const [action, setAction] = useState("");
  const { data } = useLoader<Row>(() => adminApi.auditLogs({ action: action || undefined, limit: 200 }), [action]);
  const rows: Row[] = data?.data || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {["", "auth.", "auth.login_failed", "auth.account_locked", "application.", "job.", "admin.", "file."].map(a => (
          <button key={a} onClick={() => setAction(a)}
                  className={`rounded-lg px-3 py-1.5 text-xs ${action === a ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {a || "All"}
          </button>
        ))}
        <span className="self-center text-xs text-[#64748B]">{data?.total ?? 0} entries</span>
      </div>
      <Table head={["When", "Who", "Action", "Record", "Details", "IP"]} empty={rows.length === 0}>
        {rows.map(l => (
          <tr key={l.id} className="border-b border-white/5 align-top">
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(l.created_at)}</td>
            <td className="px-4 py-3 text-xs text-white">{l.actor_email || "—"}</td>
            <td className="px-4 py-3 text-xs text-[#3B82F6] whitespace-nowrap">{l.action}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{l.entity_type ? `${l.entity_type} #${l.entity_id ?? ""}` : "—"}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] max-w-xs break-words">{l.details ? JSON.stringify(l.details) : ""}</td>
            <td className="px-4 py-3 text-xs text-[#64748B]">{l.ip_address || "—"}</td>
          </tr>
        ))}
      </Table>
    </div>
  );
}

function EmailsTab() {
  const [status, setStatus] = useState("failed");
  const { data, reload } = useLoader<Row>(() => adminApi.emails({ status: status || undefined, limit: 200 }), [status]);
  const rows: Row[] = data?.data || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {["failed", "dead", "pending", "sent", ""].map(s => (
          <button key={s} onClick={() => setStatus(s)}
                  className={`rounded-lg px-3 py-1.5 text-xs ${status === s ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {s || "All"}
          </button>
        ))}
        <Button variant="outline" className="ml-auto border-white/10" onClick={() => act(() => adminApi.retryFailedEmails(), reload)}>
          <RefreshCw className="mr-2 h-4 w-4" /> Retry all failed
        </Button>
      </div>
      <p className="text-xs text-[#64748B]">Failed emails are retried automatically after 1 min, 5 min, 15 min, 1 h and 6 h; after that they are marked dead and can be re-sent here.</p>
      <Table head={["Created", "Type", "To", "Subject", "Status", "Attempts", "Last error", ""]} empty={rows.length === 0}>
        {rows.map(r => (
          <tr key={r.id} className="border-b border-white/5 align-top">
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(r.created_at)}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8]">{r.category}</td>
            <td className="px-4 py-3 text-xs text-white">{r.to_email}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8]">{r.subject}</td>
            <td className={`px-4 py-3 text-xs ${r.status === "sent" ? "text-green-400" : r.status === "pending" ? "text-yellow-400" : "text-red-400"}`}>{r.status}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8]">{r.attempts}</td>
            <td className="px-4 py-3 text-xs text-red-300 max-w-xs break-words">{r.last_error || ""}</td>
            <td className="px-4 py-3 text-right text-xs">
              {r.status !== "sent" && <button onClick={() => act(() => adminApi.retryEmail(r.id), reload)} className="text-[#3B82F6] hover:underline">Retry</button>}
            </td>
          </tr>
        ))}
      </Table>
    </div>
  );
}

function EnquiriesTab() {
  const [status, setStatus] = useState("new");
  const [open, setOpen] = useState<number | null>(null);
  const { data, reload } = useLoader<Row>(() => adminApi.enquiries({ status: status || undefined, limit: 200 }), [status]);
  const rows: Row[] = data?.data || [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {[["new", "New"], ["handled", "Handled"], ["", "All"]].map(([s, label]) => (
          <button key={s} onClick={() => setStatus(s)}
                  className={`rounded-lg px-3 py-1.5 text-xs ${status === s ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {label}{s === "new" && data ? ` (${data.new})` : ""}
          </button>
        ))}
      </div>
      <p className="text-xs text-[#64748B]">Messages from the website contact form. Each one is also emailed to the team inbox. Click a row to read it.</p>
      <Table head={["Received", "From", "Subject", "Status", ""]} empty={rows.length === 0}>
        {rows.map(e => (
          <Fragment key={e.id}>
            <tr onClick={() => setOpen(open === e.id ? null : e.id)} className="cursor-pointer border-b border-white/5 align-top hover:bg-white/5">
              <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(e.created_at)}</td>
              <td className="px-4 py-3 text-xs">
                <div className="text-white">{e.name}</div>
                <div className="text-[#94A3B8]">{e.email}</div>
              </td>
              <td className="px-4 py-3 text-xs text-white">{e.subject}</td>
              <td className={`px-4 py-3 text-xs ${e.status === "new" ? "text-yellow-400" : "text-green-400"}`}>{e.status}</td>
              <td className="px-4 py-3 text-right text-xs whitespace-nowrap space-x-3" onClick={ev => ev.stopPropagation()}>
                <a href={`mailto:${e.email}?subject=${encodeURIComponent(`Re: ${e.subject}`)}`} className="text-[#3B82F6] hover:underline">Reply</a>
                {e.status === "new"
                  ? <button onClick={() => act(() => adminApi.markEnquiryHandled(e.id), reload)} className="text-green-300 hover:underline">Mark handled</button>
                  : <button onClick={() => act(() => adminApi.reopenEnquiry(e.id), reload)} className="text-yellow-300 hover:underline">Reopen</button>}
              </td>
            </tr>
            {open === e.id && (
              <tr className="border-b border-white/5">
                <td colSpan={5} className="px-4 pb-4 text-sm text-[#CBD5E1] whitespace-pre-wrap break-words">{e.message}</td>
              </tr>
            )}
          </Fragment>
        ))}
      </Table>
    </div>
  );
}

function NewsletterTab() {
  const [status, setStatus] = useState("confirmed");
  const [page, setPage] = useState(0);
  const { data, reload } = useLoader<Row>(
    () => adminApi.subscribers({ status: status || undefined, skip: page * 100, limit: 100 }), [status, page]);
  const rows: Row[] = data?.data || [];
  const counts: Row = data?.counts || {};
  const sendNow = async () => {
    if (!confirm("Send this week's job alert to all confirmed subscribers now? Anyone who received one in the last 6 days is skipped.")) return;
    try {
      const r = await adminApi.sendDigestNow();
      alert(r.data.message);
      reload();
    } catch (e) {
      alert(apiError(e, "Could not send the job alert"));
    }
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {[["confirmed", "Confirmed"], ["pending", "Awaiting confirmation"], ["unsubscribed", "Unsubscribed"], ["", "All"]].map(([s, label]) => (
          <button key={s} onClick={() => { setStatus(s); setPage(0); }}
                  className={`rounded-lg px-3 py-1.5 text-xs ${status === s ? "bg-white/15 text-white" : "bg-white/5 text-[#94A3B8]"}`}>
            {label}{s && counts[s] !== undefined ? ` (${counts[s]})` : ""}
          </button>
        ))}
        <Button variant="outline" className="ml-auto border-white/10" onClick={sendNow}>
          <Send className="mr-2 h-4 w-4" /> Send job alert now
        </Button>
      </div>
      <p className="text-xs text-[#64748B]">Confirmed subscribers automatically get an email with the newest jobs every Monday at 9:00 AM IST (only when new jobs were posted that week).</p>
      <Table head={["Email", "Signed up", "Confirmed", "Last job alert", "Unsubscribed"]} empty={rows.length === 0}>
        {rows.map(s => (
          <tr key={s.id} className="border-b border-white/5">
            <td className="px-4 py-3 text-xs text-white">{s.email}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(s.created_at)}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(s.confirmed_at)}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(s.last_digest_at)}</td>
            <td className="px-4 py-3 text-xs text-[#94A3B8] whitespace-nowrap">{when(s.unsubscribed_at)}</td>
          </tr>
        ))}
      </Table>
      <div className="flex justify-center gap-2">
        <Button variant="outline" className="border-white/10" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
        <Button variant="outline" className="border-white/10" disabled={rows.length < 100} onClick={() => setPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}

export default function PlatformAdminDashboardPage() {
  const router = useRouter();
  const { user, hydrated, logout } = useAuthStore();

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace("/auth/signin");
      return;
    }
    if (user.role !== "platform_admin") {
      router.replace(dashboardPathForRole(user.role));
    }
  }, [user, hydrated, router]);

  if (!hydrated || !user || user.role !== "platform_admin") {
    return <div className="flex min-h-[50vh] items-center justify-center text-[#94A3B8]">Loading…</div>;
  }

  const tabs: [string, string, React.ComponentType<{ className?: string }>][] = [
    ["overview", "Overview", Shield], ["users", "Users", Users], ["companies", "Companies", Building2],
    ["jobs", "Jobs", Briefcase], ["enquiries", "Enquiries", Inbox], ["newsletter", "Newsletter", Newspaper],
    ["audit", "Audit log", FileText], ["emails", "Emails", Mail],
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="glass-card mb-8 flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#EF4444] to-[#8B5CF6]">
            <Shield className="h-7 w-7 text-white" />
          </div>
          <div>
            <p className="text-sm text-[#94A3B8]">Platform admin</p>
            <h1 className="font-heading text-2xl font-bold text-white">{user.name}</h1>
            <p className="text-sm text-[#94A3B8]">{user.email}</p>
          </div>
        </div>
        <Button variant="outline" className="border-white/10" onClick={() => { logout(); router.push("/"); }}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </Button>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <div className="overflow-x-auto">
          <TabsList className="border border-white/10 bg-white/5">
            {tabs.map(([value, label, Icon]) => (
              <TabsTrigger key={value} value={value} className="data-[state=active]:bg-white/10">
                <Icon className="mr-2 h-4 w-4" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <TabsContent value="overview" className="mt-6"><Overview /></TabsContent>
        <TabsContent value="users" className="mt-6"><UsersTab /></TabsContent>
        <TabsContent value="companies" className="mt-6"><CompaniesTab /></TabsContent>
        <TabsContent value="jobs" className="mt-6"><JobsTab /></TabsContent>
        <TabsContent value="enquiries" className="mt-6"><EnquiriesTab /></TabsContent>
        <TabsContent value="newsletter" className="mt-6"><NewsletterTab /></TabsContent>
        <TabsContent value="audit" className="mt-6"><AuditTab /></TabsContent>
        <TabsContent value="emails" className="mt-6"><EmailsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
