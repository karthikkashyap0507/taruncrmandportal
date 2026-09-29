"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Shield, Users, Building2, Briefcase, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { useAuthStore } from "@/store/auth-store";

export default function PlatformAdminDashboardPage() {
  const router = useRouter();
  const { user, hydrated, logout } = useAuthStore();

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace("/auth/signin");
      return;
    }
    if (user.role !== "platform_admin") {
      router.replace(dashboardPathForRole(user.role));
    }
  }, [user, hydrated, router]);

  if (!hydrated || !user || user.role !== "platform_admin") {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-[#94A3B8]">
        Loading…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="glass-card flex flex-col gap-6 p-8 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#EF4444] to-[#8B5CF6]">
            <Shield className="h-7 w-7 text-white" />
          </div>
          <div>
            <p className="text-sm text-[#94A3B8]">Platform admin</p>
            <h1 className="font-heading text-2xl font-bold text-white">{user.name}</h1>
            <p className="text-sm text-[#94A3B8]">{user.email}</p>
          </div>
        </div>
        <Button
          variant="outline"
          className="border-white/10"
          onClick={() => {
            logout();
            router.push("/");
          }}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </Button>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-white/5 border border-white/10">
          <TabsTrigger value="overview" className="data-[state=active]:bg-white/10">
            <Shield className="mr-2 h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="users" className="data-[state=active]:bg-white/10">
            <Users className="mr-2 h-4 w-4" />
            Users
          </TabsTrigger>
          <TabsTrigger value="companies" className="data-[state=active]:bg-white/10">
            <Building2 className="mr-2 h-4 w-4" />
            Companies
          </TabsTrigger>
          <TabsTrigger value="jobs" className="data-[state=active]:bg-white/10">
            <Briefcase className="mr-2 h-4 w-4" />
            Jobs
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-white/10">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="bg-white/5 border-white/10">
              <CardHeader>
                <CardTitle className="text-white">Platform Stats</CardTitle>
                <CardDescription className="text-[#94A3B8]">Live platform metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-[#94A3B8]">Platform management interface</p>
              </CardContent>
            </Card>
            <Card className="bg-white/5 border-white/10">
              <CardHeader>
                <CardTitle className="text-white">User Management</CardTitle>
                <CardDescription className="text-[#94A3B8]">Manage all platform users</CardDescription>
              </CardHeader>
            </Card>
            <Card className="bg-white/5 border-white/10">
              <CardHeader>
                <CardTitle className="text-white">System Settings</CardTitle>
                <CardDescription className="text-[#94A3B8]">Configure platform settings</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="users" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Users className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">User Management</h3>
            <p className="text-[#94A3B8]">View and manage all platform users</p>
          </div>
        </TabsContent>

        <TabsContent value="companies" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Building2 className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Company Management</h3>
            <p className="text-[#94A3B8]">View and manage all companies on the platform</p>
          </div>
        </TabsContent>

        <TabsContent value="jobs" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Briefcase className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Job Management</h3>
            <p className="text-[#94A3B8]">Moderate and manage all job postings</p>
          </div>
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Settings className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Platform Settings</h3>
            <p className="text-[#94A3B8]">Configure global platform settings</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}