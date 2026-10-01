"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { interviewsApi, candidatesApi, jobsApi, apiError } from "@/lib/api";
import toast from "react-hot-toast";
import { Plus, Calendar, Clock, Video, Phone, MapPin } from "lucide-react";
import { format } from "date-fns";

const IV_TYPES = ["video", "phone", "in_person", "technical", "hr"];
const IV_STATUSES = ["scheduled", "completed", "cancelled", "no_show"];
const STATUS_COLORS: Record<string, string> = {
  scheduled: "badge-blue", completed: "badge-green", cancelled: "badge-red", no_show: "badge-yellow",
};
const TYPE_ICONS: Record<string, any> = {
  video: Video, phone: Phone, in_person: MapPin, technical: Clock, hr: Calendar,
};

function ScheduleForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ candidate_id: "", job_id: "", type: "video", scheduled_at: "", duration_minutes: 60, location_or_link: "", notes: "" });
  const [saving, setSaving] = useState(false);

  const { data: candidates } = useQuery({ queryKey: ["candidates-list"], queryFn: () => candidatesApi.list({ limit: 100 }).then(r => r.data.data) });
  const { data: jobs } = useQuery({ queryKey: ["jobs-list"], queryFn: () => jobsApi.list({ limit: 100 }).then(r => r.data.data) });

  async function save() {
    if (!form.candidate_id || !form.job_id || !form.scheduled_at) return toast.error("Fill all required fields");
    setSaving(true);
    try {
      await interviewsApi.schedule({ ...form, candidate_id: parseInt(form.candidate_id), job_id: parseInt(form.job_id) });
      toast.success("Interview scheduled");
      onSaved(); onClose();
    } catch (e: any) { toast.error(apiError(e, "Failed")); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">Schedule Interview</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Candidate *</label>
            <select className="input" value={form.candidate_id} onChange={e => setForm({ ...form, candidate_id: e.target.value })}>
              <option value="">Select candidate...</option>
              {candidates?.map((c: any) => <option key={c.id} value={c.id}>{c.name} — {c.current_title || c.email}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job *</label>
            <select className="input" value={form.job_id} onChange={e => setForm({ ...form, job_id: e.target.value })}>
              <option value="">Select job...</option>
              {jobs?.map((j: any) => <option key={j.id} value={j.id}>{j.title} — {j.client_name || "Internal"}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
              <select className="input" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                {IV_TYPES.map(t => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Duration (minutes)</label>
              <input type="number" className="input" value={form.duration_minutes} onChange={e => setForm({ ...form, duration_minutes: parseInt(e.target.value) })} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date & Time *</label>
            <input type="datetime-local" className="input" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Location / Meeting Link</label>
            <input className="input" placeholder="Zoom link or office address" value={form.location_or_link} onChange={e => setForm({ ...form, location_or_link: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="input h-16 resize-none" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Scheduling..." : "Schedule"}</button>
        </div>
      </div>
    </div>
  );
}

export default function InterviewsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: interviews = [], isLoading } = useQuery({
    queryKey: ["interviews"],
    queryFn: () => interviewsApi.list().then(r => r.data),
  });

  const upcoming = interviews.filter((iv: any) =>
    iv.status === "scheduled" && new Date(iv.scheduled_at) >= new Date()
  );
  const past = interviews.filter((iv: any) =>
    iv.status !== "scheduled" || new Date(iv.scheduled_at) < new Date()
  );

  function InterviewCard({ iv }: { iv: any }) {
    const TypeIcon = TYPE_ICONS[iv.type] || Calendar;
    return (
      <div className="card p-4 flex items-start gap-4">
        <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center flex-shrink-0">
          <TypeIcon size={18} className="text-brand-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <p className="font-medium text-gray-800 capitalize">{iv.type.replace("_", " ")} Interview</p>
            <span className={`badge ${STATUS_COLORS[iv.status] || "badge-gray"}`}>{iv.status}</span>
          </div>
          <p className="text-xs text-gray-500 flex items-center gap-1.5">
            <Calendar size={11} />
            {format(new Date(iv.scheduled_at), "EEEE, MMM d yyyy 'at' h:mm a")}
            {iv.duration_minutes && <span className="text-gray-400">· {iv.duration_minutes}m</span>}
          </p>
          {iv.location_or_link && (
            <p className="text-xs text-blue-500 mt-1 truncate">{iv.location_or_link}</p>
          )}
          {iv.feedback && <p className="text-xs text-gray-500 mt-1 italic">{iv.feedback}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Interviews</h1>
          <p className="text-sm text-gray-500">{upcoming.length} upcoming</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
          <Plus size={15} /> Schedule Interview
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}</div>
      ) : (
        <>
          {upcoming.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-600">Upcoming</h2>
              {upcoming.map((iv: any) => <InterviewCard key={iv.id} iv={iv} />)}
            </div>
          )}
          {past.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-600">Past</h2>
              {past.map((iv: any) => <InterviewCard key={iv.id} iv={iv} />)}
            </div>
          )}
          {interviews.length === 0 && (
            <div className="card p-12 text-center text-gray-400">
              <Calendar size={32} className="mx-auto mb-3 text-gray-300" />
              No interviews scheduled yet
            </div>
          )}
        </>
      )}

      {showForm && <ScheduleForm onClose={() => setShowForm(false)} onSaved={() => qc.invalidateQueries({ queryKey: ["interviews"] })} />}
    </div>
  );
}
