"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { Plus, Trash2, Check, Clock, AlertCircle } from "lucide-react";
import { format } from "date-fns";

const PRIORITIES = ["low", "medium", "high", "urgent"];
const STATUSES = ["todo", "in_progress", "review", "done"];
const PRIORITY_COLORS: Record<string, string> = {
  urgent: "badge-red", high: "badge-yellow", medium: "badge-blue", low: "badge-gray",
};

function TaskForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ title: "", description: "", priority: "medium", due_date: "" });
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!form.title.trim()) return toast.error("Title required");
    setSaving(true);
    try {
      await tasksApi.create({ ...form, due_date: form.due_date || undefined });
      toast.success("Task created");
      onSaved();
      onClose();
    } catch {
      toast.error("Failed to create task");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">New Task</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} autoFocus />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea className="input h-20 resize-none" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
              <select className="input" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                {PRIORITIES.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Due Date</label>
              <input type="datetime-local" className="input" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Creating..." : "Create Task"}</button>
        </div>
      </div>
    </div>
  );
}

export default function TasksPage() {
  const qc = useQueryClient();
  const me = useAuthStore(s => s.user);
  const canDelete = (task: any) => me?.role === "owner" || task.created_by_id === me?.id;
  const [showForm, setShowForm] = useState(false);
  const [myOnly, setMyOnly] = useState(true);
  const [filter, setFilter] = useState("");

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", myOnly],
    queryFn: () => tasksApi.list({ assigned_to_me: myOnly }).then(r => r.data),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => tasksApi.update(id, { status: "done" }),
    onSuccess: () => { toast.success("Task completed"); qc.invalidateQueries({ queryKey: ["tasks"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to update task")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tasksApi.delete(id),
    onSuccess: () => { toast.success("Task deleted"); qc.invalidateQueries({ queryKey: ["tasks"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to delete task")),
  });

  const filtered = tasks.filter((t: any) =>
    !filter || t.status === filter
  );

  const grouped = STATUSES.reduce((acc, s) => {
    acc[s] = filtered.filter((t: any) => t.status === s);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Tasks</h1>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={myOnly} onChange={e => setMyOnly(e.target.checked)} className="rounded" />
            My tasks only
          </label>
          <select className="input w-36 text-sm" value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">All Status</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.replace("_", " ").charAt(0).toUpperCase() + s.replace("_", " ").slice(1)}</option>)}
          </select>
          <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> New Task
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {STATUSES.map(status => (
            <div key={status} className="space-y-2">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  {status.replace("_", " ")}
                </h3>
                <span className="badge badge-gray">{grouped[status]?.length || 0}</span>
              </div>
              {grouped[status]?.length === 0 && (
                <div className="h-20 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center">
                  <p className="text-xs text-gray-400">No tasks</p>
                </div>
              )}
              {grouped[status]?.map((task: any) => (
                <div key={task.id} className="card p-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-sm font-medium ${task.status === "done" ? "line-through text-gray-400" : "text-gray-800"}`}>
                      {task.title}
                    </p>
                    <span className={`badge ${PRIORITY_COLORS[task.priority] || "badge-gray"} flex-shrink-0`}>
                      {task.priority}
                    </span>
                  </div>
                  {task.description && <p className="text-xs text-gray-500 line-clamp-2">{task.description}</p>}
                  {task.due_date && (
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Clock size={11} />
                      {format(new Date(task.due_date), "MMM d, h:mm a")}
                    </div>
                  )}
                  <div className="flex items-center gap-1 pt-1">
                    {task.status !== "done" && (
                      <button
                        onClick={() => completeMutation.mutate(task.id)}
                        className="p-1.5 hover:bg-green-50 rounded text-gray-400 hover:text-green-600 transition-colors"
                        title="Mark done"
                      >
                        <Check size={13} />
                      </button>
                    )}
                    {canDelete(task) && (
                      <button
                        onClick={() => { if (confirm("Delete task?")) deleteMutation.mutate(task.id); }}
                        className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <TaskForm onClose={() => setShowForm(false)} onSaved={() => qc.invalidateQueries({ queryKey: ["tasks"] })} />
      )}
    </div>
  );
}
