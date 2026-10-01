"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi, apiError } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { Plus, Trash2, Edit2, ShieldCheck, Shield, User } from "lucide-react";
import { format } from "date-fns";

const ROLES = ["owner", "bdm", "hr"];
const ROLE_ICONS: Record<string, any> = {
  owner: ShieldCheck,
  bdm: Shield,
  hr: User,
};
const ROLE_COLORS: Record<string, string> = {
  owner: "badge-purple", bdm: "badge-blue", hr: "badge-green",
};

function UserForm({ user, onClose, onSaved }: { user?: any; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: user?.name || "",
    email: user?.email || "",
    phone: user?.phone || "",
    role: user?.role || "hr",
    password: "",
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      if (user?.id) {
        await usersApi.update(user.id, { name: form.name, phone: form.phone, role: form.role });
      } else {
        if (!form.password || form.password.length < 8) return toast.error("Password must be at least 8 characters");
        await usersApi.create(form);
      }
      toast.success(user?.id ? "User updated" : "User created");
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(apiError(e, "Failed to save"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">{user?.id ? "Edit User" : "Add Team Member"}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>
        </div>
        <div className="p-5 space-y-4">
          {[
            { label: "Full Name *", key: "name", required: true },
            { label: "Email *", key: "email", type: "email", required: true, disabled: !!user?.id },
            { label: "Phone", key: "phone" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
              <input
                type={f.type || "text"}
                className="input disabled:bg-gray-50 disabled:text-gray-400"
                value={(form as any)[f.key]}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                disabled={f.disabled}
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
            <select className="input" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
              {ROLES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
            </select>
          </div>
          {!user?.id && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Password *</label>
              <input type="password" className="input" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} minLength={8} />
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 p-5 border-t">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">{saving ? "Saving..." : user?.id ? "Update" : "Create"}</button>
        </div>
      </div>
    </div>
  );
}

export default function TeamPage() {
  const qc = useQueryClient();
  const currentUser = useAuthStore(s => s.user);
  const [showForm, setShowForm] = useState(false);
  const [editUser, setEditUser] = useState<any>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["team-users"],
    queryFn: () => usersApi.list().then(r => r.data),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => usersApi.delete(id),
    onSuccess: () => { toast.success("User deactivated"); qc.invalidateQueries({ queryKey: ["team-users"] }); },
    onError: (e: any) => toast.error(apiError(e, "Failed")),
  });

  if (!currentUser || currentUser.role !== "owner") {
    return (
      <div className="p-6">
        <div className="card p-10 text-center">
          <ShieldCheck size={40} className="text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Only Owners can manage team members.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Team</h1>
          <p className="text-sm text-gray-500">{users.length} members</p>
        </div>
        <button onClick={() => { setEditUser(null); setShowForm(true); }} className="btn-primary flex items-center gap-2">
          <Plus size={15} /> Add Member
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />)
        ) : users.map((u: any) => {
          const RoleIcon = ROLE_ICONS[u.role] || User;
          return (
            <div key={u.id} className={`card p-5 ${!u.is_active ? "opacity-50" : ""}`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-brand-100 flex items-center justify-center">
                    <span className="text-brand-700 font-bold">{u.name[0].toUpperCase()}</span>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{u.name}</p>
                    <span className={`badge ${ROLE_COLORS[u.role] || "badge-gray"}`}>
                      <RoleIcon size={10} className="mr-1 inline" />{u.role}
                    </span>
                  </div>
                </div>
                {!u.is_active && <span className="badge badge-red">Inactive</span>}
              </div>
              <p className="text-xs text-gray-500 mb-1">{u.email}</p>
              {u.phone && <p className="text-xs text-gray-400 mb-2">{u.phone}</p>}
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-50">
                <p className="text-xs text-gray-400">
                  Last login: {u.last_login ? format(new Date(u.last_login), "MMM d") : "Never"}
                </p>
                {u.id !== currentUser.id && u.is_active && (
                  <div className="flex gap-1">
                    <button onClick={() => { setEditUser(u); setShowForm(true); }} className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-brand-600">
                      <Edit2 size={13} />
                    </button>
                    <button
                      onClick={() => { if (confirm(`Deactivate ${u.name}?`)) deactivateMutation.mutate(u.id); }}
                      className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {showForm && (
        <UserForm
          user={editUser}
          onClose={() => setShowForm(false)}
          onSaved={() => qc.invalidateQueries({ queryKey: ["team-users"] })}
        />
      )}
    </div>
  );
}
