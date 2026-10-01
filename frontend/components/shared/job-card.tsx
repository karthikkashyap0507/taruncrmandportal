"use client";

import { motion } from "framer-motion";
import { Bookmark, BookmarkCheck, Briefcase, ExternalLink, GraduationCap, MapPin, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApplyDialog } from "@/components/shared/apply-dialog";
import { educationLabel, formatPlace, formatSalary } from "@/lib/format";
import { savedJobsApi } from "@/services/api";
import { useAuthStore } from "@/store/auth-store";
import type { Job } from "@/types";

interface JobCardProps {
  job: Job;
  index?: number;
  initialSaved?: boolean;
  onApplied?: (jobId: number) => void;
}

export function JobCard({ job, index = 0, initialSaved = false, onApplied }: JobCardProps) {
  const { user } = useAuthStore();
  const [saved, setSaved] = useState(initialSaved);
  const [savingState, setSavingState] = useState(false);
  const [applied, setApplied] = useState(false);
  const [showApplyDialog, setShowApplyDialog] = useState(false);

  const companyName = job.company?.name || "Company";
  const companyInitial = companyName.charAt(0).toUpperCase();
  const isRemote = job.location?.toLowerCase().includes("remote") ?? false;

  const toggleSave = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) { window.location.href = "/auth/signin"; return; }
    setSavingState(true);
    try {
      if (saved) {
        await savedJobsApi.unsave(job.id);
        setSaved(false);
      } else {
        await savedJobsApi.save(job.id);
        setSaved(true);
      }
    } catch (err: any) {
      if (err?.response?.status === 201 || err?.response?.status === 200) setSaved(true);
    } finally {
      setSavingState(false);
    }
  };

  const handleApplyClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) { window.location.href = "/auth/signin"; return; }
    if (user.role !== "candidate") { alert("Only candidates can apply for jobs."); return; }
    setShowApplyDialog(true);
  };

  const salaryColors = ["text-[#10B981]", "text-[#06B6D4]", "text-[#F59E0B]"];
  const colorIdx = job.id % salaryColors.length;

  return (
    <>
    {showApplyDialog && (
      <ApplyDialog
        job={job}
        isOpen={showApplyDialog}
        onClose={() => setShowApplyDialog(false)}
        onSuccess={() => { setApplied(true); onApplied?.(job.id); }}
        initialName={user?.name || ""}
      />
    )}
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className="glass-card group relative overflow-hidden p-5 sm:p-6"
    >
      <motion.div
        className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[#3B82F6]/10 blur-2xl"
        animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
        transition={{ duration: 4, repeat: Infinity }}
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[#3B82F6]/5 to-[#8B5CF6]/5 opacity-0 transition-opacity group-hover:opacity-100" />

      <div className="relative flex flex-col gap-4">
        {/* Company + Save */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] text-lg font-bold text-white shadow-lg">
              {companyInitial}
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-white group-hover:text-[#3B82F6] transition-colors line-clamp-1">
                {job.title}
              </h3>
              <p className="text-sm text-[#94A3B8] line-clamp-1">{companyName}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {isRemote && <Badge className="border-0 bg-[#06B6D4]/20 text-[#06B6D4] text-xs">Remote</Badge>}
            <button
              onClick={toggleSave}
              disabled={savingState}
              className={`rounded-lg p-1.5 transition-all ${saved ? "text-[#F59E0B] bg-[#F59E0B]/10" : "text-[#94A3B8] hover:text-[#F59E0B] hover:bg-[#F59E0B]/10"}`}
              title={saved ? "Unsave job" : "Save job"}
            >
              {saved ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap gap-3 text-sm text-[#94A3B8]">
          <span className="flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-[#3B82F6]" />
            {formatPlace(job.location, job.locality) || "Remote"}
          </span>
          <span className="flex items-center gap-1">
            <Briefcase className="h-3.5 w-3.5 text-[#8B5CF6]" />
            {job.experience_level || "All levels"}
          </span>
          {job.education && (
            <span className="flex items-center gap-1">
              <GraduationCap className="h-3.5 w-3.5 text-[#10B981]" />
              {educationLabel(job.education)}
            </span>
          )}
          {(job.salary_min || job.salary_max) && (
            <span className={`font-semibold ${salaryColors[colorIdx]}`}>
              {formatSalary(job.salary_min, job.salary_max, job.salary_period)}
            </span>
          )}
          {job.employment_type && (
            <Badge variant="outline" className="border-white/10 text-xs capitalize">
              {job.employment_type.replace("_", " ")}
            </Badge>
          )}
        </div>

        {/* Skills */}
        {job.skills?.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {job.skills.slice(0, 4).map((skill, i) => (
              <Badge key={i} variant="outline" className="border-white/10 bg-white/5 text-xs text-[#94A3B8]">
                {skill}
              </Badge>
            ))}
            {job.skills.length > 4 && (
              <Badge variant="outline" className="border-white/10 bg-white/5 text-xs text-[#64748B]">
                +{job.skills.length - 4}
              </Badge>
            )}
          </div>
        )}

        {/* Description preview */}
        {job.description && (
          <p className="text-xs text-[#64748B] line-clamp-2">{job.description}</p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            size="sm"
            onClick={handleApplyClick}
            disabled={applied}
            className={`flex-1 transition-all ${applied ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30" : "bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] hover:opacity-90"}`}
          >
            {applied ? "✓ Applied" : <span className="flex items-center gap-1"><Zap className="h-3.5 w-3.5" /> AI Apply</span>}
          </Button>
          <Link href={`/jobs/${job.id}`}>
            <Button size="sm" variant="outline" className="border-white/10 bg-white/5 hover:bg-white/10">
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      </div>
    </motion.article>
    </>
  );
}
