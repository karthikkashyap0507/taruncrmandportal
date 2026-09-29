"use client";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";

const COLORS = ["#7c3aed", "#3b82f6", "#f59e0b", "#ec4899", "#f97316", "#22c55e", "#ef4444", "#6b7280"];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-base font-semibold text-gray-800 mb-4">{children}</h2>;
}

export default function AnalyticsPage() {
  const { data: overview } = useQuery({ queryKey: ["analytics-overview"], queryFn: () => analyticsApi.overview().then(r => r.data) });
  const { data: trend } = useQuery({ queryKey: ["leads-trend"], queryFn: () => analyticsApi.leadsTrend(30).then(r => r.data) });
  const { data: pipeline } = useQuery({ queryKey: ["leads-pipeline"], queryFn: () => analyticsApi.leadsPipeline().then(r => r.data) });
  const { data: candStatus } = useQuery({ queryKey: ["cand-status"], queryFn: () => analyticsApi.candidatesByStatus().then(r => r.data) });
  const { data: team } = useQuery({ queryKey: ["team-perf"], queryFn: () => analyticsApi.teamPerformance().then(r => r.data) });
  const { data: revenue } = useQuery({ queryKey: ["revenue"], queryFn: () => analyticsApi.revenue().then(r => r.data) });

  const pipelineData = pipeline?.map((p: any, i: number) => ({
    name: p.status.charAt(0).toUpperCase() + p.status.slice(1),
    count: p.count,
    fill: COLORS[i % COLORS.length],
  })) || [];

  const candData = candStatus?.map((c: any, i: number) => ({
    name: c.status.charAt(0).toUpperCase() + c.status.slice(1),
    value: c.count,
    color: COLORS[i % COLORS.length],
  })) || [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Analytics & Reports</h1>

      {/* Summary row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Leads", value: overview?.leads?.total ?? "—" },
          { label: "Conversion Rate", value: `${overview?.leads?.conversion_rate ?? 0}%` },
          { label: "Candidates Placed", value: overview?.candidates?.placed ?? "—" },
          { label: "Pipeline Value", value: revenue ? `₹${Number(revenue.total_pipeline_value).toLocaleString()}` : "—" },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-gray-500 mb-1">{s.label}</p>
            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Lead trend */}
      <div className="card p-5">
        <SectionTitle>Leads Trend (Last 30 Days)</SectionTitle>
        {trend?.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} labelFormatter={l => `Date: ${l}`} />
              <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2.5} dot={false} name="Leads" />
            </LineChart>
          </ResponsiveContainer>
        ) : <p className="text-sm text-gray-400 text-center py-8">No trend data</p>}
      </div>

      {/* Pipeline + Candidates */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <SectionTitle>Lead Pipeline Distribution</SectionTitle>
          {pipelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={pipelineData} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" name="Leads" radius={[4, 4, 0, 0]}>
                  {pipelineData.map((entry: any, i: number) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-400 text-center py-8">No data</p>}
        </div>

        <div className="card p-5">
          <SectionTitle>Candidate Status</SectionTitle>
          {candData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={candData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45}>
                  {candData.map((entry: any, i: number) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-400 text-center py-8">No candidates</p>}
        </div>
      </div>

      {/* Team Performance */}
      {team?.length > 0 && (
        <div className="card p-5">
          <SectionTitle>Team Performance (Last 30 Days)</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left">
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Name</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Role</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Leads Assigned</th>
                  <th className="px-4 py-2.5 text-xs font-semibold text-gray-500">Performance</th>
                </tr>
              </thead>
              <tbody>
                {team.map((member: any) => {
                  const maxLeads = Math.max(...team.map((m: any) => m.leads_assigned), 1);
                  const pct = Math.round((member.leads_assigned / maxLeads) * 100);
                  return (
                    <tr key={member.user_id} className="border-b border-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{member.name}</td>
                      <td className="px-4 py-3 capitalize text-gray-500">{member.role}</td>
                      <td className="px-4 py-3 text-gray-700">{member.leads_assigned}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-500 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-gray-500 w-8">{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
