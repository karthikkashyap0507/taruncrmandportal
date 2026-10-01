"use client";

import { useState, useRef } from "react";
import { Briefcase, FileText, Loader2, Phone, Send, Upload, User, X, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { jobsApi, uploadApi } from "@/services/api";
import { EDUCATION_OPTIONS } from "@/lib/format";
import type { ApplicationCreate, Job } from "@/types";

interface ApplyDialogProps {
  job: Job;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialName?: string;
  initialEmail?: string;
}

export function ApplyDialog({ job, isOpen, onClose, onSuccess, initialName = "", initialEmail = "" }: ApplyDialogProps) {
  const [form, setForm] = useState<ApplicationCreate & { name: string; email: string }>({
    name: initialName,
    email: initialEmail,
    full_name: initialName,
    phone: "",
    years_experience: undefined,
    cover_letter: "",
    resume_url: "",
    education: undefined,
    expected_salary: undefined,
    current_location: "",
  });
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setResumeFile(file);
  };

  const handleSubmit = async () => {
    if (!form.phone) { setError("Phone number is required"); return; }
    setError("");
    setSubmitting(true);
    try {
      let resumeUrl = form.resume_url;

      // Upload resume if a file was selected
      if (resumeFile) {
        setUploading(true);
        try {
          const uploadRes = await uploadApi.uploadResume(resumeFile);
          resumeUrl = uploadRes.data.url;
        } catch (e) {
          setError("Failed to upload resume. Please try again.");
          setSubmitting(false);
          setUploading(false);
          return;
        }
        setUploading(false);
      }

      const payload: ApplicationCreate = {
        full_name: form.full_name || form.name,
        phone: form.phone,
        years_experience: form.years_experience ? Number(form.years_experience) : undefined,
        cover_letter: form.cover_letter,
        resume_url: resumeUrl,
        education: form.education || undefined,
        expected_salary: form.expected_salary || undefined,
        current_location: form.current_location?.trim() || undefined,
      };

      await jobsApi.apply(job.id, payload);
      onSuccess();
      onClose();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      if (detail?.includes("Already applied")) {
        onSuccess(); // treat as success
        onClose();
      } else {
        setError(detail || "Failed to submit application. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-2xl rounded-2xl border border-white/10 bg-[#0F172A] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="border-b border-white/10 bg-gradient-to-r from-[#3B82F6]/10 to-[#8B5CF6]/10 px-6 py-4">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">Apply for Position</h2>
              <div className="mt-1 flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-[#3B82F6]" />
                <span className="text-sm font-medium text-[#3B82F6]">{job.title}</span>
                {job.company && <span className="text-sm text-[#94A3B8]">at {job.company.name}</span>}
              </div>
            </div>
            <button onClick={onClose} className="rounded-lg p-1.5 text-[#94A3B8] hover:bg-white/10 hover:text-white transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Form */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Personal Details */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="text-[#94A3B8] text-xs flex items-center gap-1"><User className="h-3 w-3" /> Full Name *</Label>
              <Input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="John Doe"
                className="border-white/10 bg-white/5 text-white"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#94A3B8] text-xs flex items-center gap-1"><Phone className="h-3 w-3" /> Phone Number *</Label>
              <Input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+91 98765 43210"
                className="border-white/10 bg-white/5 text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="text-[#94A3B8] text-xs">Years of Experience</Label>
              <Input
                type="number"
                min={0}
                max={50}
                value={form.years_experience ?? ""}
                onChange={(e) => setForm({ ...form, years_experience: parseInt(e.target.value) || undefined })}
                placeholder="e.g. 3"
                className="border-white/10 bg-white/5 text-white"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="apply-education" className="text-[#94A3B8] text-xs">Highest Qualification</Label>
              <select
                id="apply-education"
                value={form.education ?? ""}
                onChange={(e) => setForm({ ...form, education: (e.target.value || undefined) as ApplicationCreate["education"] })}
                className="h-9 w-full rounded-md border border-white/10 bg-[#0F172A] px-3 text-sm text-white"
              >
                <option value="">Select</option>
                {EDUCATION_OPTIONS.filter(o => o.value !== "any").map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#94A3B8] text-xs">Expected Salary (₹ per month)</Label>
              <Input
                type="number"
                min={0}
                value={form.expected_salary ?? ""}
                onChange={(e) => setForm({ ...form, expected_salary: parseInt(e.target.value) || undefined })}
                placeholder="e.g. 20000"
                className="border-white/10 bg-white/5 text-white"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#94A3B8] text-xs">Current Location</Label>
              <Input
                value={form.current_location ?? ""}
                onChange={(e) => setForm({ ...form, current_location: e.target.value })}
                placeholder="e.g. JP Nagar, Bengaluru"
                className="border-white/10 bg-white/5 text-white"
              />
            </div>
          </div>

          {/* Cover Letter */}
          <div className="space-y-1.5">
            <Label className="text-[#94A3B8] text-xs">Cover Letter / Message to Recruiter</Label>
            <Textarea
              value={form.cover_letter}
              onChange={(e) => setForm({ ...form, cover_letter: e.target.value })}
              placeholder={`Hi, I'm excited to apply for the ${job.title} position. I believe my experience in ${job.skills?.slice(0, 2).join(" and ") || "this field"} makes me a great fit...`}
              className="border-white/10 bg-white/5 text-white min-h-[120px]"
            />
          </div>

          {/* Resume Upload */}
          <div className="space-y-3">
            <Label className="text-[#94A3B8] text-xs flex items-center gap-1"><FileText className="h-3 w-3" /> Resume</Label>
            <div className="grid gap-3 sm:grid-cols-2">
              {/* File upload */}
              <div
                onClick={() => fileRef.current?.click()}
                className={`cursor-pointer rounded-xl border-2 border-dashed p-4 text-center transition-colors ${resumeFile ? "border-[#10B981]/50 bg-[#10B981]/5" : "border-white/10 hover:border-[#3B82F6]/50 hover:bg-[#3B82F6]/5"}`}
              >
                <input ref={fileRef} type="file" accept=".pdf,.doc,.docx" onChange={handleFileChange} className="hidden" />
                {resumeFile ? (
                  <>
                    <FileText className="mx-auto mb-2 h-6 w-6 text-[#10B981]" />
                    <p className="text-xs text-[#10B981] font-medium">{resumeFile.name}</p>
                    <p className="text-xs text-[#64748B] mt-1">{(resumeFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  </>
                ) : (
                  <>
                    <Upload className="mx-auto mb-2 h-6 w-6 text-[#94A3B8]" />
                    <p className="text-xs text-[#94A3B8]">Click to upload PDF, DOC, DOCX</p>
                    <p className="text-xs text-[#64748B] mt-1">Max 5MB</p>
                  </>
                )}
              </div>
              {/* OR URL */}
              <div className="space-y-1.5">
                <p className="text-xs text-[#64748B] text-center">or paste a link</p>
                <Input
                  value={form.resume_url}
                  onChange={(e) => setForm({ ...form, resume_url: e.target.value })}
                  placeholder="https://drive.google.com/..."
                  className="border-white/10 bg-white/5 text-white text-xs"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-white/10 px-6 py-4 flex items-center justify-between gap-3">
          <p className="text-xs text-[#64748B]">Your details are shared only with the hiring team.</p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} className="border-white/10 bg-white/5">Cancel</Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || uploading}
              className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
            >
              {uploading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
              ) : submitting ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Submitting...</>
              ) : (
                <><Zap className="mr-2 h-4 w-4" /> Submit Application</>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
