"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, apiError } from "@/lib/api";
import toast from "react-hot-toast";
import { Building2, Phone, Mail, Plus, TrendingUp } from "lucide-react";
import { useState } from "react";

const STAGES = [
  { key: "new", label: "New", color: "bg-gray-100 border-gray-200" },
  { key: "contacted", label: "Contacted", color: "bg-blue-50 border-blue-200" },
  { key: "qualified", label: "Qualified", color: "bg-yellow-50 border-yellow-200" },
  { key: "proposal", label: "Proposal", color: "bg-pink-50 border-pink-200" },
  { key: "negotiation", label: "Negotiation", color: "bg-orange-50 border-orange-200" },
  { key: "converted", label: "Converted", color: "bg-green-50 border-green-200" },
];

const TEMP_EMOJI: Record<string, string> = { hot: "🔥", warm: "☀️", cold: "❄️" };

function LeadCard({ lead, onDragStart }: { lead: any; onDragStart: (e: any, lead: any) => void }) {
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead)}
      className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-semibold text-gray-800 leading-tight">{lead.company_name}</p>
        <span className="text-sm flex-shrink-0">{TEMP_EMOJI[lead.temperature]}</span>
      </div>
      <p className="text-xs text-gray-500 mb-2">{lead.contact_name}{lead.contact_designation ? `, ${lead.contact_designation}` : ""}</p>
      {lead.requirement && <p className="text-xs text-gray-400 line-clamp-2 mb-2">{lead.requirement}</p>}
      <div className="flex items-center gap-2 flex-wrap">
        {lead.industry && (
          <span className="badge badge-gray">{lead.industry}</span>
        )}
        {lead.budget && (
          <span className="text-xs text-green-600 font-medium">₹{Number(lead.budget).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

function Column({ stage, leads, onDrop, onDragOver }: { stage: any; leads: any[]; onDrop: (e: any, status: string) => void; onDragOver: (e: any) => void }) {
  const [isOver, setIsOver] = useState(false);

  return (
    <div className="flex flex-col w-64 flex-shrink-0">
      <div className={`rounded-t-lg border-t border-x px-3 py-2.5 ${stage.color}`}>
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold text-gray-700">{stage.label}</p>
          <span className="badge badge-gray">{leads.length}</span>
        </div>
      </div>
      <div
        onDragOver={(e) => { e.preventDefault(); setIsOver(true); onDragOver(e); }}
        onDragLeave={() => setIsOver(false)}
        onDrop={(e) => { setIsOver(false); onDrop(e, stage.key); }}
        className={`flex-1 min-h-64 border border-t-0 rounded-b-lg p-2 space-y-2 transition-colors ${stage.color} ${isOver ? "ring-2 ring-brand-500 ring-inset" : ""}`}
      >
        {leads.map(lead => (
          <LeadCard key={lead.id} lead={lead} onDragStart={(e, l) => e.dataTransfer.setData("leadId", String(l.id))} />
        ))}
        {leads.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">Drop leads here</p>
        )}
      </div>
    </div>
  );
}

export default function PipelinePage() {
  const qc = useQueryClient();
  const { data: pipeline, isLoading } = useQuery({
    queryKey: ["pipeline"],
    queryFn: () => leadsApi.pipeline().then(r => r.data),
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => leadsApi.updateStatus(id, status),
    onSuccess: () => { toast.success("Lead moved"); qc.invalidateQueries({ queryKey: ["pipeline"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed to move lead")),
  });

  function handleDrop(e: React.DragEvent, toStatus: string) {
    const leadId = parseInt(e.dataTransfer.getData("leadId"));
    if (leadId) updateStatus.mutate({ id: leadId, status: toStatus });
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STAGES.map(s => (
            <div key={s.key} className="w-64 flex-shrink-0 h-96 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const total = STAGES.reduce((acc, s) => acc + (pipeline?.[s.key]?.length || 0), 0);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Lead Pipeline</h1>
          <p className="text-sm text-gray-500">{total} leads · Drag to move between stages</p>
        </div>
        <div className="flex gap-2">
          <a href="/leads" className="btn-secondary flex items-center gap-2"><TrendingUp size={15} /> List View</a>
          <a href="/leads?new=1" className="btn-primary flex items-center gap-2"><Plus size={15} /> Add Lead</a>
        </div>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map(stage => (
          <Column
            key={stage.key}
            stage={stage}
            leads={pipeline?.[stage.key] || []}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          />
        ))}
      </div>
    </div>
  );
}
