"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { Lock, Monitor, Shield, User } from "lucide-react";
import { apiError, authApi, usersApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

function Devices() {
  const qc = useQueryClient();
  const { clearAuth } = useAuthStore();
  const { data: sessions, isLoading } = useQuery({ queryKey: ["sessions"], queryFn: () => authApi.sessions().then(r => r.data) });

  async function revoke(id: number) {
    try {
      await authApi.revokeSession(id);
      toast.success("Device signed out");
      qc.invalidateQueries({ queryKey: ["sessions"] });
    } catch (e) {
      toast.error(apiError(e, "Could not sign that device out"));
    }
  }

  async function signOutEverywhere() {
    if (!confirm("Sign out of every device, including this one?")) return;
    try {
      await authApi.logoutAll();
    } finally {
      clearAuth();
      window.location.href = "/login";
    }
  }

  const device = (ua?: string) => {
    if (!ua) return "Unknown device";
    const os = /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Mac/.test(ua) ? "macOS" : /Linux/.test(ua) ? "Linux" : "Device";
    const browser = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "Browser";
    return `${browser} on ${os}`;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-gray-700">Signed-in devices</h3>
        <button onClick={signOutEverywhere} className="btn-secondary text-xs">Sign out everywhere</button>
      </div>
      {isLoading ? <div className="h-10 bg-gray-100 rounded animate-pulse" /> : (sessions || []).map((s: any) => (
        <div key={s.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100">
          <Monitor size={18} className="text-gray-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-800">{device(s.device_info)} {s.current && <span className="badge badge-green ml-1">This device</span>}</p>
            <p className="text-xs text-gray-400">
              {s.ip_address || "unknown IP"} · last active {s.last_used_at ? format(new Date(s.last_used_at), "dd MMM yyyy, HH:mm") : "—"}
            </p>
          </div>
          {!s.current && <button onClick={() => revoke(s.id)} className="text-xs text-red-600 hover:underline">Sign out</button>}
        </div>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  const { user, setAuth, refreshToken } = useAuthStore();
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState({ name: user?.name || "", phone: user?.phone || "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm: "" });
  const [saving, setSaving] = useState(false);

  async function saveProfile() {
    setSaving(true);
    try {
      const res = await usersApi.updateMe({ name: profile.name, phone: profile.phone || undefined });
      setAuth(res.data, localStorage.getItem("crm_access_token") || "", refreshToken || "");
      toast.success("Profile updated");
    } catch (e) {
      toast.error(apiError(e, "Failed to update profile"));
    } finally {
      setSaving(false);
    }
  }

  async function changePassword() {
    if (passwords.new_password !== passwords.confirm) return toast.error("The new passwords don't match");
    if (passwords.new_password.length < 8) return toast.error("Use at least 8 characters");
    setSaving(true);
    try {
      await authApi.changePassword(passwords.current_password, passwords.new_password);
      toast.success("Password changed. Your other devices have been signed out.");
      setPasswords({ current_password: "", new_password: "", confirm: "" });
    } catch (e) {
      toast.error(apiError(e, "Failed to change password"));
    } finally {
      setSaving(false);
    }
  }

  const TABS = [
    { key: "profile", label: "Profile", icon: User },
    { key: "security", label: "Security", icon: Lock },
    { key: "permissions", label: "Permissions", icon: Shield },
  ];
  const role = user?.role;
  const PERMISSIONS = [
    { label: "Leads", value: role === "hr" ? "Only leads assigned to you" : "All leads" },
    { label: "Reassign / delete leads", value: role === "hr" ? "Restricted" : "Allowed" },
    { label: "Clients", value: role === "hr" ? "View only" : role === "bdm" ? "Add and edit" : "Add, edit and delete" },
    { label: "Candidates", value: role === "owner" ? "Full access, including delete and merge" : "Add and edit" },
    { label: "Jobs", value: role === "hr" ? "View and manage pipelines" : role === "bdm" ? "Create and edit" : "Create, edit and delete" },
    { label: "Placements", value: role === "hr" ? "Your placements" : "All placements" },
    { label: "MOUs and invoices", value: role === "owner" ? "Full access, approve and mark paid" : role === "bdm" ? "Create and raise" : "Restricted" },
    { label: "Incentives", value: role === "owner" ? "Everyone's, set rates and approve" : "Your own (read only)" },
    { label: "Revenue analytics", value: role === "hr" ? "Restricted" : "Allowed" },
    { label: "Team, audit log, email log", value: role === "owner" ? "Allowed" : "Restricted" },
  ];

  return (
    <div className="p-4 sm:p-6 max-w-3xl">
      <h1 className="text-xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="card overflow-hidden">
        <div className="flex border-b border-gray-100 overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${
                tab === t.key ? "text-brand-600 border-brand-600" : "text-gray-500 border-transparent hover:text-gray-700"
              }`}
            >
              <t.icon size={15} />
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-4 sm:p-6">
          {tab === "profile" && (
            <div className="space-y-5">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">
                  {user?.name?.[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{user?.name}</p>
                  <p className="text-sm text-gray-500">{user?.email}</p>
                  <span className="badge badge-purple mt-1">{user?.role}</span>
                </div>
              </div>
              {[
                { label: "Full Name", key: "name" },
                { label: "Phone", key: "phone" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
                  <input className="input" value={(profile as any)[f.key]}
                         onChange={e => setProfile({ ...profile, [f.key]: e.target.value })} />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                <input className="input bg-gray-50 text-gray-400" value={user?.email} disabled />
                <p className="text-xs text-gray-400 mt-1">Email can only be changed by the owner</p>
              </div>
              <button onClick={saveProfile} disabled={saving} className="btn-primary">{saving ? "Saving..." : "Save Profile"}</button>
            </div>
          )}

          {tab === "security" && (
            <div className="space-y-8">
              <div className="space-y-5 max-w-sm">
                <p className="text-sm text-gray-600">Change your password. Other devices are signed out; this one stays signed in.</p>
                {[
                  { label: "Current Password", key: "current_password" },
                  { label: "New Password", key: "new_password" },
                  { label: "Confirm New Password", key: "confirm" },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
                    <input type="password" className="input" value={(passwords as any)[f.key]}
                           onChange={e => setPasswords({ ...passwords, [f.key]: e.target.value })} />
                  </div>
                ))}
                <button onClick={changePassword} disabled={saving} className="btn-primary">{saving ? "Changing..." : "Change Password"}</button>
              </div>
              <Devices />
            </div>
          )}

          {tab === "permissions" && (
            <div className="space-y-2">
              <p className="text-sm text-gray-600 mb-4">What your role ({role}) can do. Enforced by the server on every request.</p>
              {PERMISSIONS.map(p => (
                <div key={p.label} className="flex items-center justify-between gap-4 py-2 border-b border-gray-50 last:border-0">
                  <p className="text-sm text-gray-700">{p.label}</p>
                  <span className={`badge ${p.value === "Restricted" ? "badge-red" : "badge-green"} text-right`}>{p.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
