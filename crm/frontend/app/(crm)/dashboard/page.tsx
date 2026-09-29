"use client";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, leadsApi, tasksApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { format } from "date-fns";
import {
  TrendingUp, Users, Briefcase, Calendar, CheckSquare,
  ArrowUpRight, Clock, Target, DollarSign,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const STATUS_COLORS: Record<string, string> = {
  new: "#7c3aed", contacted: "#3b82f6", qualified: "#f59e0b",
  proposal: "#ec4899", negotiation: "#f97316", converted: "#22c55e",
  lost: "#ef4444", cold: "#6b7280",
};

function StatCard({ label, value, sub, icon: Icon, color }: any) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={18} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value ?? "—"}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data: overview } = useQuery({ queryKey: ["analytics-overview"], queryFn: () => analyticsApi.overview().then(r => r.data) });
  const { data: trend } = useQuery({ queryKey: ["leads-trend"], queryFn: () => analyticsApi.leadsTrend(30).then(r => r.data) });
  const { data: pipeline } = useQuery({ queryKey: ["leads-pipeline"], queryFn: () => analyticsApi.leadsPipeline().then(r => r.data) });
  const { data: myTasks } = useQuery({
    queryKey: ["my-tasks"],
    queryFn: () => tasksApi.list({ assigned_to_me: true }).then(r => r.data),
  });

  const pieData = pipeline?.map((p: any) => ({
    name: p.status.charAt(0).toUpperCase() + p.status.slice(1),
    value: p.count,
    color: STATUS_COLORS[p.status] || "#9ca3af",
  })) || [];

  const pendingTasks = myTasks?.filter((t: any) => t.status !== "done") || [];
  const dueSoon = pendingTasks.filter((t: any) => {
    if (!t.due_date) return false;
    const diff = (new Date(t.due_date).getTime() - Date.now()) / 86400000;
    return diff <= 2 && diff >= 0;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">
          Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}, {user?.name?.split(" ")[0]}
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">{format(new Date(), "EEEE, MMMM d, yyyy")}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Leads"
          value={overview?.leads?.total}
          sub={`${overview?.leads?.this_month || 0} this month`}
          icon={TrendingUp}
          color="bg-brand-600"
        />
        <StatCard
          label="Conversion Rate"
          value={`${overview?.leads?.conversion_rate || 0}%`}
          sub={`${overview?.leads?.converted || 0} converted`}
          icon={Target}
          color="bg-green-500"
        />
        <StatCard
          label="Active Candidates"
          value={overview?.candidates?.active}
          sub={`${overview?.candidates?.placed || 0} placed`}
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          label="Open Jobs"
          value={overview?.jobs?.open}
          sub={`${overview?.interviews?.today || 0} interviews today`}
          icon={Briefcase}
          color="bg-orange-500"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Lead trend */}
        <div className="card p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Leads — Last 30 Days</h2>
          {trend?.length ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={v => v.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, fontSize: 12, border: "1px solid #e5e7eb" }}
                  labelFormatter={l => `Date: ${l}`}
                />
                <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">No data yet</div>
          )}
        </div>

        {/* Pipeline pie */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Lead Pipeline</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
                  {pieData.map((entry: any, i: number) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">No leads yet</div>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pending tasks */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">My Tasks</h2>
            <a href="/tasks" className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
              View all <ArrowUpRight size={12} />
            </a>
          </div>
          {pendingTasks.length === 0 ? (
            <p className="text-sm text-gray-400 py-4 text-center">No pending tasks</p>
          ) : (
            <div className="space-y-2">
              {pendingTasks.slice(0, 5).map((task: any) => (
                <div key={task.id} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    task.priority === "urgent" ? "bg-red-500" :
                    task.priority === "high" ? "bg-orange-400" :
                    task.priority === "medium" ? "bg-yellow-400" : "bg-gray-300"
                  }`} />
                  <p className="text-sm text-gray-700 flex-1 truncate">{task.title}</p>
                  {task.due_date && (
                    <span className="text-xs text-gray-400 flex items-center gap-1 flex-shrink-0">
                      <Clock size={10} />
                      {format(new Date(task.due_date), "MMM d")}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Add Lead", href: "/leads?new=1", icon: TrendingUp, color: "bg-brand-50 text-brand-700 hover:bg-brand-100" },
              { label: "Add Candidate", href: "/candidates?new=1", icon: Users, color: "bg-blue-50 text-blue-700 hover:bg-blue-100" },
              { label: "Post Job", href: "/jobs?new=1", icon: Briefcase, color: "bg-orange-50 text-orange-700 hover:bg-orange-100" },
              { label: "Schedule Interview", href: "/interviews?new=1", icon: Calendar, color: "bg-green-50 text-green-700 hover:bg-green-100" },
            ].map(action => (
              <a
                key={action.href}
                href={action.href}
                className={`flex items-center gap-2 p-3 rounded-lg ${action.color} transition-colors text-sm font-medium`}
              >
                <action.icon size={16} />
                {action.label}
              </a>
            ))}
          </div>

          {dueSoon.length > 0 && (
            <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-xs font-semibold text-yellow-700 mb-1">Due Soon</p>
              {dueSoon.slice(0, 2).map((t: any) => (
                <p key={t.id} className="text-xs text-yellow-600 truncate">{t.title}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
