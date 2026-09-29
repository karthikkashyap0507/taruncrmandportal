"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, LogOut, Users, Briefcase, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { useAuthStore } from "@/store/auth-store";
import { jobsApi } from "@/services/api";
import type { Job, Company } from "@/types";

export default function CompanyAdminDashboardPage() {
  const router = useRouter();
  const { user, hydrated, logout } = useAuthStore();
  const [company, setCompany] = useState<Company | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace("/auth/signin");
      return;
    }
    if (user.role !== "company_admin") {
      router.replace(dashboardPathForRole(user.role));
    }
    if (user && user.role === "company_admin") {
      loadCompanyData();
    }
  }, [user, hydrated, router]);

  const loadCompanyData = async () => {
    try {
      const [companyRes, jobsRes] = await Promise.all([
        jobsApi.getMyCompany(),
        jobsApi.listMy(),
      ]);
      setCompany(companyRes.data);
      setJobs(jobsRes.data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to load company data", err);
      setLoading(false);
    }
  };

  if (!hydrated || !user || user.role !== "company_admin") {
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
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-[#10B981] to-[#3B82F6]">
            <Building2 className="h-7 w-7 text-white" />
          </div>
          <div>
            <p className="text-sm text-[#94A3B8]">Company admin dashboard</p>
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
            <Building2 className="mr-2 h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="jobs" className="data-[state=active]:bg-white/10">
            <Briefcase className="mr-2 h-4 w-4" />
            Jobs
          </TabsTrigger>
          <TabsTrigger value="team" className="data-[state=active]:bg-white/10">
            <Users className="mr-2 h-4 w-4" />
            Team
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-white/10">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          {loading ? (
            <div className="grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="bg-white/5 border-white/10">
                  <CardHeader>
                    <div className="h-6 w-3/4 bg-white/10 rounded animate-pulse" />
                  </CardHeader>
                  <CardContent>
                    <div className="h-8 w-1/2 bg-white/10 rounded animate-pulse" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="bg-white/5 border-white/10">
                <CardHeader>
                  <CardTitle className="text-white">Company</CardTitle>
                  <CardDescription className="text-[#94A3B8]">{company?.name}</CardDescription>
                </CardHeader>
                <CardContent>
                  {company?.industry && (
                    <Badge className="bg-blue-500/20 text-blue-400">{company.industry}</Badge>
                  )}
                </CardContent>
              </Card>
              <Card className="bg-white/5 border-white/10">
                <CardHeader>
                  <CardTitle className="text-white">Total Jobs</CardTitle>
                  <CardDescription className="text-[#94A3B8]">Active job postings</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-white">{jobs.length}</p>
                </CardContent>
              </Card>
              <Card className="bg-white/5 border-white/10">
                <CardHeader>
                  <CardTitle className="text-white">Published Jobs</CardTitle>
                  <CardDescription className="text-[#94A3B8]">Live on the platform</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-white">
                    {jobs.filter(j => j.status === "published").length}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="jobs" className="mt-6">
          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="bg-white/5 border-white/10">
                  <CardHeader>
                    <div className="h-6 w-3/4 bg-white/10 rounded animate-pulse" />
                    <div className="h-4 w-1/2 bg-white/10 rounded animate-pulse" />
                  </CardHeader>
                </Card>
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Briefcase className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No jobs posted yet</h3>
              <p className="text-[#94A3B8]">Create job postings to start hiring</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {jobs.map((job) => (
                <Card key={job.id} className="bg-white/5 border-white/10">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-white text-lg">{job.title}</CardTitle>
                        <CardDescription className="text-[#94A3B8]">
                          {job.location || "Remote"}
                        </CardDescription>
                      </div>
                      <Badge className={
                        job.status === "published" ? "bg-green-500/20 text-green-400" :
                        job.status === "draft" ? "bg-yellow-500/20 text-yellow-400" :
                        "bg-red-500/20 text-red-400"
                      }>
                        {job.status}
                      </Badge>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="team" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Users className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Team Management</h3>
            <p className="text-[#94A3B8]">Invite and manage recruiters for your company</p>
          </div>
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <div className="glass-card p-12 text-center">
            <Settings className="mx-auto h-12 w-12 text-[#94A3B8] mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Company Settings</h3>
            <p className="text-[#94A3B8]">Update your company profile and preferences</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}