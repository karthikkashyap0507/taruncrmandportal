"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { authApi, notificationsApi } from "@/lib/api";
import toast from "react-hot-toast";
import {
  LayoutDashboard, Users, Building2, UserCheck, Briefcase,
  KanbanSquare, Calendar, BarChart3, ClipboardList, Settings,
  Bell, LogOut, Menu, X, ChevronDown,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: KanbanSquare },
  { href: "/pipeline", label: "Pipeline", icon: KanbanSquare },
  { href: "/clients", label: "Clients", icon: Building2 },
  { href: "/candidates", label: "Candidates", icon: UserCheck },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/interviews", label: "Interviews", icon: Calendar },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/team", label: "Team", icon: Users, ownerOnly: true },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function CRMLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, clearAuth, refreshToken } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notifCount, setNotifCount] = useState(0);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Wait for Zustand persist to rehydrate from localStorage before checking auth
  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated && !user) {
      router.replace("/login");
    }
  }, [hydrated, user, router]);

  useEffect(() => {
    if (!user) return;
    notificationsApi.unreadCount()
      .then(res => setNotifCount(res.data.count))
      .catch(() => {});
    const interval = setInterval(() => {
      notificationsApi.unreadCount()
        .then(res => setNotifCount(res.data.count))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [user]);

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {}
    clearAuth();
    router.push("/login");
    toast.success("Logged out");
  }

  // Show spinner while Zustand is rehydrating
  if (!hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const visibleNav = navItems.filter(item => !item.ownerOnly || user.role === "owner");

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-30
        w-60 bg-white border-r border-gray-200 flex flex-col
        transform transition-transform duration-200
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-gray-100">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white text-sm font-bold">J</span>
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900 leading-none">JobsNexGen</p>
            <p className="text-xs text-gray-400">CRM Platform</p>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
          {visibleNav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <a
                key={item.href}
                href={item.href}
                className={`sidebar-link ${active ? "active" : "text-gray-600"}`}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon size={18} className="flex-shrink-0" />
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-100 p-3">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-3 w-full px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs font-bold">{user.name[0].toUpperCase()}</span>
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user.name}</p>
                <p className="text-xs text-gray-400 capitalize">{user.role}</p>
              </div>
              <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
            </button>

            {userMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
                <a href="/settings" className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  <Settings size={14} /> Settings
                </a>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                >
                  <LogOut size={14} /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-4 gap-4 flex-shrink-0">
          <button
            className="lg:hidden text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={22} />
          </button>

          <div className="flex-1" />

          {/* Notifications */}
          <a href="/notifications" className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell size={20} />
            {notifCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-white text-[10px] font-bold flex items-center justify-center">
                {notifCount > 9 ? "9+" : notifCount}
              </span>
            )}
          </a>

          {/* Role badge */}
          <span className={`badge ${user.role === "owner" ? "badge-purple" : user.role === "bdm" ? "badge-blue" : "badge-green"}`}>
            {user.role.toUpperCase()}
          </span>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
