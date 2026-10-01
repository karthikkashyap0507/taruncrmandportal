"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Bookmark, BookmarkCheck, Briefcase, Check,
  Copy, Link2, MapPin, Share2, X, Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ApplyDialog } from "@/components/shared/apply-dialog";
import { jobsApi, savedJobsApi, apiError } from "@/services/api";
import { formatSalary } from "@/lib/format";
import { useAuthStore } from "@/store/auth-store";
import type { Job } from "@/types";

// ── WhatsApp icon (not in lucide) ─────────────────────────────────────────────
function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
    </svg>
  );
}

// ── Share modal ───────────────────────────────────────────────────────────────
function ShareModal({ job, onClose }: { job: Job; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);
  const url = typeof window !== "undefined" ? window.location.href : `https://jobsnexgen.com/jobs/${job.id}`;
  const text = `Check out this job: ${job.title} at ${job.company?.name || "a great company"} on JobsNexGen!`;

  const shares = [
    {
      label: "WhatsApp",
      icon: <WhatsAppIcon className="h-5 w-5" />,
      color: "bg-[#25D366]/10 border-[#25D366]/30 text-[#25D366] hover:bg-[#25D366]/20",
      href: `https://wa.me/?text=${encodeURIComponent(text + "\n" + url)}`,
    },
    {
      label: "LinkedIn",
      icon: (
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>
      ),
      color: "bg-[#0A66C2]/10 border-[#0A66C2]/30 text-[#0A66C2] hover:bg-[#0A66C2]/20",
      href: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
    },
    {
      label: "Facebook",
      icon: (
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>
      ),
      color: "bg-[#1877F2]/10 border-[#1877F2]/30 text-[#1877F2] hover:bg-[#1877F2]/20",
      href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(text)}`,
    },
  ];

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const el = document.createElement("textarea");
      el.value = url;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      ref={overlayRef}
      onClick={e => { if (e.target === overlayRef.current) onClose(); }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
    >
      <div className="w-full max-w-sm rounded-2xl bg-[#0F172A] border border-white/10 shadow-2xl p-6 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-white font-semibold text-lg">Share this Job</h3>
            <p className="text-[#64748B] text-xs mt-0.5 truncate max-w-[240px]">{job.title} · {job.company?.name}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-[#64748B] hover:text-white hover:bg-white/10 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Share buttons */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {shares.map(({ label, icon, color, href }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={`flex flex-col items-center gap-2 rounded-xl border px-3 py-4 text-xs font-medium transition-all ${color}`}
            >
              {icon}
              {label}
            </a>
          ))}
        </div>

        {/* Copy link */}
        <div className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 px-3 py-2.5">
          <Link2 className="h-4 w-4 text-[#64748B] shrink-0" />
          <span className="flex-1 text-xs text-[#94A3B8] truncate">{url}</span>
          <button
            onClick={copyLink}
            className={`shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
              copied
                ? "bg-green-500/20 text-green-400 border border-green-500/30"
                : "bg-[#3B82F6]/20 text-[#3B82F6] border border-[#3B82F6]/30 hover:bg-[#3B82F6]/30"
            }`}
          >
            {copied ? <><Check className="h-3 w-3" /> Copied!</> : <><Copy className="h-3 w-3" /> Copy</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function JobDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuthStore();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [applied, setApplied] = useState(false);
  const [showApplyDialog, setShowApplyDialog] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [saved, setSaved] = useState(false);
  const [savingJob, setSavingJob] = useState(false);

  useEffect(() => {
    if (params.id) loadJob();
  }, [params.id]);

  useEffect(() => {
    if (job && user) checkSaved();
  }, [job, user]);

  const loadJob = async () => {
    try {
      const res = await jobsApi.get(parseInt(params.id as string));
      setJob(res.data);
    } catch (err) {
      console.error("Failed to load job", err);
    } finally {
      setLoading(false);
    }
  };

  const checkSaved = async () => {
    if (!job) return;
    try {
      const res = await savedJobsApi.check(job.id);
      setSaved(res.data.saved);
    } catch { /* unauthenticated - ignore */ }
  };

  const handleSave = async () => {
    if (!user) { router.push("/auth/signin"); return; }
    if (!job) return;
    setSavingJob(true);
    try {
      if (saved) {
        await savedJobsApi.unsave(job.id);
        setSaved(false);
      } else {
        await savedJobsApi.save(job.id);
        setSaved(true);
      }
    } catch (e) {
      alert(apiError(e, "Could not update saved jobs"));
    }
    finally { setSavingJob(false); }
  };

  const handleApplyClick = () => {
    if (!user) { router.push("/auth/signin"); return; }
    if (user.role !== "candidate") { alert("Only candidates can apply for jobs."); return; }
    setShowApplyDialog(true);
  };

  if (loading) {
    return (
      <div className="pb-24 pt-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <Button variant="outline" className="mb-8 border-white/10 bg-white/5" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Jobs
          </Button>
          <Skeleton className="h-12 w-3/4 rounded-xl mb-4" />
          <Skeleton className="h-6 w-1/2 rounded-xl mb-8" />
          <div className="glass-card p-8">
            <Skeleton className="h-6 w-1/3 rounded-xl mb-4" />
            <Skeleton className="h-4 w-full rounded-xl mb-2" />
            <Skeleton className="h-4 w-5/6 rounded-xl mb-2" />
            <Skeleton className="h-4 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="pb-24 pt-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Job not found</h2>
          <Button variant="outline" className="border-white/10 bg-white/5" onClick={() => router.push("/jobs")}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Jobs
          </Button>
        </div>
      </div>
    );
  }

  const companyName = job.company?.name || "Company";
  const companyInitial = companyName.charAt(0);

  return (
    <div className="pb-24 pt-12">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <Button variant="outline" className="mb-8 border-white/10 bg-white/5" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Jobs
        </Button>

        <div className="glass-card mb-8 p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] text-xl font-bold text-white shrink-0">
                {companyInitial}
              </div>
              <div>
                <h1 className="font-heading text-3xl font-bold text-white mb-2">{job.title}</h1>
                <p className="text-lg text-[#94A3B8] mb-4">{companyName}</p>
                <div className="flex flex-wrap gap-4">
                  <span className="flex items-center gap-2 text-[#94A3B8]">
                    <MapPin className="h-5 w-5 text-[#3B82F6]" />
                    {job.location || "Remote"}
                  </span>
                  <span className="flex items-center gap-2 text-[#94A3B8]">
                    <Briefcase className="h-5 w-5 text-[#8B5CF6]" />
                    {job.experience_level || "Entry Level"}
                  </span>
                  <span className="text-lg font-semibold text-[#10B981]">
                    {formatSalary(job.salary_min, job.salary_max)}
                  </span>
                </div>
              </div>
            </div>

            {/* Save + Share */}
            <div className="flex gap-2 shrink-0">
              <Button
                size="sm"
                variant="outline"
                onClick={handleSave}
                disabled={savingJob}
                title={saved ? "Remove from saved" : "Save job"}
                className={`border-white/10 transition-all ${
                  saved
                    ? "bg-[#F59E0B]/15 border-[#F59E0B]/40 text-[#F59E0B] hover:bg-[#F59E0B]/25"
                    : "bg-white/5 text-[#94A3B8] hover:text-[#F59E0B] hover:border-[#F59E0B]/30"
                }`}
              >
                {saved
                  ? <BookmarkCheck className="h-4 w-4" />
                  : <Bookmark className="h-4 w-4" />}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowShare(true)}
                title="Share job"
                className="border-white/10 bg-white/5 text-[#94A3B8] hover:text-[#3B82F6] hover:border-[#3B82F6]/30 transition-all"
              >
                <Share2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <Separator className="my-8 bg-white/10" />

          <div className="flex flex-wrap gap-3 mb-8">
            {(job.skills || []).map((skill, i) => (
              <Badge key={i} variant="secondary" className="bg-white/10 text-white">{skill}</Badge>
            ))}
          </div>

          <Button
            size="lg"
            className="w-full sm:w-auto bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] hover:opacity-90"
            onClick={handleApplyClick}
            disabled={applied}
          >
            <Zap className="mr-2 h-5 w-5" />
            {applied ? "✓ Applied" : "AI Apply Now"}
          </Button>
        </div>

        <Card className="bg-white/5 border-white/10">
          <CardHeader>
            <CardTitle className="text-white text-xl">Job Description</CardTitle>
            <CardDescription className="text-[#94A3B8]">
              Learn more about this role and what we're looking for
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose prose-invert max-w-none">
              <p className="text-[#94A3B8] whitespace-pre-wrap">{job.description}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {showApplyDialog && job && (
        <ApplyDialog
          job={job}
          isOpen={showApplyDialog}
          onClose={() => setShowApplyDialog(false)}
          onSuccess={() => { setApplied(true); setShowApplyDialog(false); }}
          initialName={user?.name || ""}
        />
      )}

      {showShare && job && (
        <ShareModal job={job} onClose={() => setShowShare(false)} />
      )}
    </div>
  );
}
