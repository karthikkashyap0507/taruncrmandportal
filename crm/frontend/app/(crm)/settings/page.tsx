"use client";
import { useState } from "react";
import { useAuthStore } from "@/store/auth";
import { usersApi, authApi } from "@/lib/api";
import toast from "react-hot-toast";
import { User, Lock, Bell, Shield } from "lucide-react";

export default function SettingsPage() {
  const { user, setAuth, refreshToken } = useAuthStore();
  const [tab, setTab] = useState("profile");
  const [profile, setProfile] = useState({ name: user?.name || "", phone: user?.phone || "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm: "" });
  const [saving, setSaving] = useState(false);

  async function saveProfile() {
    setSaving(true);
    try {
      const res = await usersApi.update(user!.id, { name: profile.name, phone: profile.phone });
      toast.success("Profile updated");
      const meRes = await authApi.me();
      setAuth(meRes.data, localStorage.getItem("crm_access_token") || "", refreshToken || "");
    } catch {
      toast.error("Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  async function changePassword() {
    if (passwords.new_password !== passwords.confirm) return toast.error("Passwords don't match");
    if (passwords.new_password.length < 8) return toast.error("Password too short");
    setSaving(true);
    try {
      await authApi.resetPassword(passwords.current_password, passwords.new_password);
      toast.success("Password changed — please log in again");
      setTimeout(() => window.location.href = "/login", 2000);
    } catch {
      toast.error("Failed to change password");
    } finally {
      setSaving(false);
    }
  }

  const TABS = [
    { key: "profile", label: "Profile", icon: User },
    { key: "security", label: "Security", icon: Lock },
    { key: "permissions", label: "Permissions", icon: Shield },
  ];

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="card overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-gray-100">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors border-b-2 ${
                tab === t.key ? "text-brand-600 border-brand-600" : "text-gray-500 border-transparent hover:text-gray-700"
              }`}
            >
              <t.icon size={15} />
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === "profile" && (
            <div className="space-y-5">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">
                  {user?.name[0].toUpperCase()}
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
                  <input
                    className="input"
                    value={(profile as any)[f.key]}
                    onChange={e => setProfile({ ...profile, [f.key]: e.target.value })}
                  />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                <input className="input bg-gray-50 text-gray-400" value={user?.email} disabled />
                <p className="text-xs text-gray-400 mt-1">Email cannot be changed</p>
              </div>
              <button onClick={saveProfile} disabled={saving} className="btn-primary">
                {saving ? "Saving..." : "Save Profile"}
              </button>
            </div>
          )}

          {tab === "security" && (
            <div className="space-y-5 max-w-sm">
              <p className="text-sm text-gray-600 mb-4">Change your password. After changing, you will be logged out.</p>
              {[
                { label: "Current Password", key: "current_password" },
                { label: "New Password", key: "new_password" },
                { label: "Confirm New Password", key: "confirm" },
              ].map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
                  <input
                    type="password"
                    className="input"
                    value={(passwords as any)[f.key]}
                    onChange={e => setPasswords({ ...passwords, [f.key]: e.target.value })}
                  />
                </div>
              ))}
              <button onClick={changePassword} disabled={saving} className="btn-primary">
                {saving ? "Changing..." : "Change Password"}
              </button>
            </div>
          )}

          {tab === "permissions" && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-4">Your current permissions based on your role.</p>
              <div className="space-y-2">
                {[
                  { label: "View Leads", allowed: true },
                  { label: "Create/Edit Leads", allowed: user?.role !== "hr" },
                  { label: "Delete Leads", allowed: user?.role === "owner" || user?.role === "bdm" },
                  { label: "Manage Team", allowed: user?.role === "owner" },
                  { label: "View Analytics", allowed: true },
                  { label: "Manage Candidates", allowed: true },
                  { label: "Post Jobs", allowed: true },
                  { label: "View Clients", allowed: true },
                ].map(p => (
                  <div key={p.label} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                    <p className="text-sm text-gray-700">{p.label}</p>
                    <span className={`badge ${p.allowed ? "badge-green" : "badge-red"}`}>
                      {p.allowed ? "Allowed" : "Restricted"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
