"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, apiError } from "@/lib/api";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { Bell, Check, CheckCheck } from "lucide-react";

const TYPE_COLORS: Record<string, string> = {
  lead: "badge-purple",
  task: "badge-blue",
  interview: "badge-yellow",
  application: "badge-green",
  system: "badge-gray",
};

export default function NotificationsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () => notificationsApi.list(unreadOnly).then(r => r.data),
  });

  const markAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      toast.success("All marked as read");
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notif-count"] });
    },
    onError: (e: any) => toast.error(apiError(e, "Failed")),
  });

  async function markRead(id: number, actionUrl?: string) {
    try {
      await notificationsApi.markRead(id);
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notif-count"] });
      if (actionUrl) router.push(actionUrl);
    } catch {
      toast.error("Failed to mark as read");
    }
  }

  const list = Array.isArray(notifications) ? notifications : [];
  const unreadCount = list.filter((n: any) => !n.read).length;

  return (
    <div className="p-6 space-y-5 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Bell size={20} className="text-brand-600" />
            Notifications
          </h1>
          <p className="text-sm text-gray-500">{unreadCount} unread</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUnreadOnly(v => !v)}
            className={`btn-secondary text-sm ${unreadOnly ? "ring-2 ring-brand-500" : ""}`}
          >
            {unreadOnly ? "Showing unread" : "Show all"}
          </button>
          <button
            onClick={() => markAllMutation.mutate()}
            disabled={unreadCount === 0}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <CheckCheck size={15} /> Mark all read
          </button>
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card p-4 h-16 animate-pulse bg-gray-50" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <div className="card p-10 text-center">
          <Bell size={32} className="text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No notifications</p>
        </div>
      ) : (
        <div className="space-y-2">
          {list.map((n: any) => (
            <div
              key={n.id}
              className={`card p-4 flex items-start gap-3 transition-colors ${
                n.read ? "bg-white" : "bg-brand-50/40 border-brand-100"
              }`}
            >
              <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${n.read ? "bg-transparent" : "bg-brand-500"}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-gray-800">{n.title}</span>
                  {n.type && <span className={`badge ${TYPE_COLORS[n.type] || "badge-gray"} text-xs`}>{n.type}</span>}
                </div>
                {n.body && <p className="text-sm text-gray-600 mt-0.5">{n.body}</p>}
                <p className="text-xs text-gray-400 mt-1">
                  {format(new Date(n.created_at), "MMM d, yyyy · h:mm a")}
                </p>
              </div>
              {!n.read && (
                <button
                  onClick={() => markRead(n.id, n.action_url)}
                  title="Mark as read"
                  className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-gray-100 rounded flex-shrink-0"
                >
                  <Check size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
