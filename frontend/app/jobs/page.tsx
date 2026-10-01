"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowUpDown, Briefcase, Building2, ChevronDown, ChevronUp,
  ExternalLink, Filter, MapPin, RefreshCw, Search, SlidersHorizontal,
  Sparkles, X, IndianRupee, Clock, Zap
} from "lucide-react";
import { useState, useEffect, useCallback, useMemo } from "react";
import { JobCard } from "@/components/shared/job-card";
import { SectionHeading } from "@/components/shared/section-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { externalJobsApi, jobsApi } from "@/services/api";
import { useAuthStore } from "@/store/auth-store";
import type { ExternalJob, Job } from "@/types";
import { EDUCATION_OPTIONS } from "@/lib/format";

// ─── Filter data ────────────────────────────────────────────────────────────
const CITIES = [
  "All Cities", "Bengaluru", "Hyderabad", "Mumbai", "Delhi", "Gurugram",
  "Noida", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Kochi", "Remote",
];

const CATEGORIES = [
  { value: "all", label: "All Categories" },
  { value: "software engineer", label: "Software Engineering" },
  { value: "frontend", label: "Frontend / UI" },
  { value: "backend", label: "Backend / API" },
  { value: "full stack", label: "Full Stack" },
  { value: "mobile", label: "Mobile (iOS/Android)" },
  { value: "data scientist", label: "Data Science / AI" },
  { value: "devops", label: "DevOps / Cloud / SRE" },
  { value: "machine learning", label: "Machine Learning" },
  { value: "product manager", label: "Product Management" },
  { value: "design", label: "Design / UX" },
  { value: "cybersecurity", label: "Cybersecurity" },
  { value: "blockchain", label: "Blockchain / Web3" },
  { value: "qa", label: "QA / Testing" },
  { value: "marketing", label: "Marketing / Growth" },
  { value: "finance", label: "Finance / FinTech" },
  { value: "hr", label: "HR / Talent" },
  { value: "sales", label: "Sales / Business Dev" },
];

const EXPERIENCE_OPTIONS = [
  { value: "all", label: "All Levels" },
  { value: "fresher", label: "Fresher / 0–1 yr" },
  { value: "1-3", label: "Junior · 1–3 yrs" },
  { value: "3-5", label: "Mid · 3–5 yrs" },
  { value: "5-8", label: "Senior · 5–8 yrs" },
  { value: "8", label: "Lead / Principal · 8+ yrs" },
];

const EMPLOYMENT_TYPES = [
  { value: "full_time", label: "Full Time" },
  { value: "part_time", label: "Part Time" },
  { value: "contract", label: "Contract" },
  { value: "internship", label: "Internship" },
  { value: "remote", label: "Remote" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
  { value: "salary_high", label: "Salary: High → Low" },
  { value: "salary_low", label: "Salary: Low → High" },
  { value: "az", label: "A → Z" },
  { value: "za", label: "Z → A" },
];

const SKILL_TAGS = ["Python", "React", "TypeScript", "AI/ML", "AWS", "Node.js", "Java", "Go", "Kubernetes", "SQL"];

// Pay filters work per month, so monthly and yearly salaries compare fairly
const SALARY_PRESETS = [
  { label: "₹10k+", value: 10000 },
  { label: "₹15k+", value: 15000 },
  { label: "₹20k+", value: 20000 },
  { label: "₹30k+", value: 30000 },
  { label: "₹50k+", value: 50000 },
  { label: "₹1L+", value: 100000 },
];

/** Monthly equivalent of a job's salary figure (older jobs without a period are yearly). */
const perMonth = (amount: number | undefined, job: Job) =>
  amount ? (job.salary_period === "month" ? amount : amount / 12) : 0;

// A candidate qualifies for jobs that ask for their level or lower
const EDUCATION_RANK: Record<string, number> = { any: 0, "10th": 1, "12th": 2, iti: 2, diploma: 3, graduate: 4, postgraduate: 5 };

// ─── Collapsible filter section ──────────────────────────────────────────────
function FilterSection({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-white/5 pb-4 last:border-0">
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-1 text-sm font-semibold text-white hover:text-[#3B82F6] transition-colors">
        {title}
        {open ? <ChevronUp className="h-4 w-4 text-[#64748B]" /> : <ChevronDown className="h-4 w-4 text-[#64748B]" />}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

// ─── Active filter chip ───────────────────────────────────────────────────────
function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#3B82F6]/15 border border-[#3B82F6]/30 px-2.5 py-0.5 text-xs text-[#3B82F6]">
      {label}
      <button onClick={onRemove} className="hover:text-white transition-colors"><X className="h-3 w-3" /></button>
    </span>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function JobsPage() {
  const { user } = useAuthStore();

  // filters
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("All Cities");
  const [category, setCategory] = useState("all");
  const [experience, setExperience] = useState("all");
  const [employmentTypes, setEmploymentTypes] = useState<string[]>([]);
  const [salaryMin, setSalaryMin] = useState(0);
  const [salaryMax, setSalaryMax] = useState(0);
  const [locality, setLocality] = useState("");
  const [education, setEducation] = useState("all");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [activeSkillTags, setActiveSkillTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("newest");
  const [showExternal, setShowExternal] = useState(true);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  // data
  const [allJobs, setAllJobs] = useState<Job[]>([]);
  const [externalJobs, setExternalJobs] = useState<ExternalJob[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 200 };
      if (query) params.q = query;
      if (activeSkillTags.length) params.q = ((params.q || "") + " " + activeSkillTags.join(" ")).trim();

      const promises: Promise<any>[] = [jobsApi.list(params), externalJobsApi.search({ q: params.q }).catch(() => null)];
      if (user?.role === "candidate") promises.push(externalJobsApi.recommendations().catch(() => null));

      const [internalRes, extRes, recRes] = await Promise.allSettled(promises);
      if (internalRes.status === "fulfilled") setAllJobs(internalRes.value.data || []);
      if (extRes.status === "fulfilled" && extRes.value?.data) {
        setAllJobs(extRes.value.data.internal || []);
        setExternalJobs(extRes.value.data.external || []);
      }
      if (recRes?.status === "fulfilled") setRecommendedJobs(recRes.value?.data || []);
    } catch {
      try { const r = await jobsApi.list({ limit: 200 }); setAllJobs(r.data); } catch {}
    } finally { setLoading(false); }
  }, [query, activeSkillTags, user?.role]);

  useEffect(() => { fetchJobs(); }, []);

  // ── Client-side filter + sort ────────────────────────────────────────────
  const filteredJobs = useMemo(() => {
    let jobs = [...allJobs];

    // City
    if (city !== "All Cities") {
      if (city === "Remote") {
        jobs = jobs.filter(j => j.location?.toLowerCase().includes("remote"));
      } else {
        jobs = jobs.filter(j => j.location?.toLowerCase().includes(city.toLowerCase()));
      }
    }
    // Area / locality (also matches the city field, for jobs that put the area there)
    if (locality.trim()) {
      const area = locality.trim().toLowerCase();
      jobs = jobs.filter(j => j.locality?.toLowerCase().includes(area) || j.location?.toLowerCase().includes(area));
    }
    // Qualification
    if (education !== "all") {
      const mine = EDUCATION_RANK[education] ?? 0;
      jobs = jobs.filter(j => !j.education || (EDUCATION_RANK[j.education] ?? 0) <= mine);
    }
    // Remote toggle
    if (remoteOnly) jobs = jobs.filter(j => j.location?.toLowerCase().includes("remote"));
    // Category
    if (category !== "all") {
      jobs = jobs.filter(j =>
        j.title.toLowerCase().includes(category.toLowerCase()) ||
        j.description?.toLowerCase().includes(category.toLowerCase()) ||
        j.skills?.some(s => s.toLowerCase().includes(category.toLowerCase()))
      );
    }
    // Experience
    if (experience !== "all") {
      jobs = jobs.filter(j =>
        !j.experience_level || j.experience_level.toLowerCase().includes(experience.toLowerCase()) ||
        experience === "fresher" && (j.experience_level.includes("0") || j.experience_level.includes("1"))
      );
    }
    // Employment type
    if (employmentTypes.length > 0) {
      jobs = jobs.filter(j => employmentTypes.includes(j.employment_type || ""));
    }
    // Salary
    if (salaryMin > 0) jobs = jobs.filter(j => perMonth(j.salary_max || j.salary_min, j) >= salaryMin);
    if (salaryMax > 0) jobs = jobs.filter(j => !j.salary_min || perMonth(j.salary_min, j) <= salaryMax);

    // Sort
    switch (sortBy) {
      case "salary_high": jobs.sort((a, b) => perMonth(b.salary_max || b.salary_min, b) - perMonth(a.salary_max || a.salary_min, a)); break;
      case "salary_low": jobs.sort((a, b) => perMonth(a.salary_min || a.salary_max, a) - perMonth(b.salary_min || b.salary_max, b)); break;
      case "az": jobs.sort((a, b) => a.title.localeCompare(b.title)); break;
      case "za": jobs.sort((a, b) => b.title.localeCompare(a.title)); break;
      case "oldest": jobs.sort((a, b) => a.id - b.id); break;
      default: jobs.sort((a, b) => b.id - a.id); // newest
    }
    return jobs;
  }, [allJobs, city, locality, education, remoteOnly, category, experience, employmentTypes, salaryMin, salaryMax, sortBy]);

  // ── Active filter count ────────────────────────────────────────────────────
  const activeFilterCount = [
    city !== "All Cities", category !== "all", experience !== "all", locality.trim() !== "", education !== "all",
    employmentTypes.length > 0, salaryMin > 0, salaryMax > 0,
    remoteOnly, activeSkillTags.length > 0,
  ].filter(Boolean).length;

  const clearFilters = () => {
    setCity("All Cities"); setCategory("all"); setExperience("all"); setLocality(""); setEducation("all");
    setEmploymentTypes([]); setSalaryMin(0); setSalaryMax(0);
    setRemoteOnly(false); setActiveSkillTags([]); setSortBy("newest");
  };

  const toggleEmploymentType = (t: string) =>
    setEmploymentTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  const toggleSkill = (s: string) =>
    setActiveSkillTags(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);

  const totalShown = filteredJobs.length + (showExternal ? externalJobs.length : 0);

  // ── Filter sidebar (shared between desktop + mobile) ──────────────────────
  const FilterPanel = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 font-semibold text-white">
          <SlidersHorizontal className="h-4 w-4 text-[#3B82F6]" /> Filters
          {activeFilterCount > 0 && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#3B82F6] text-[10px] font-bold text-white">
              {activeFilterCount}
            </span>
          )}
        </span>
        {activeFilterCount > 0 && (
          <button onClick={clearFilters} className="text-xs text-[#94A3B8] hover:text-white transition-colors">
            Clear all
          </button>
        )}
      </div>

      {/* City */}
      <FilterSection title="City / Location">
        {/* compact 2-up controls: fine on phones */}
        <div className="grid grid-cols-2 gap-1.5">
          {CITIES.map(c => (
            <button key={c} onClick={() => setCity(c)}
              className={`rounded-lg px-2 py-1.5 text-xs font-medium text-left transition-all ${
                city === c ? "bg-[#3B82F6] text-white" : "bg-white/5 text-[#94A3B8] hover:bg-white/10 hover:text-white"
              }`}>
              {c === "Remote" ? "🌐 Remote" : c === "All Cities" ? "All" : c}
            </button>
          ))}
        </div>
      </FilterSection>

      {/* Area / locality */}
      <FilterSection title="Area / Locality">
        <Input placeholder="e.g. JP Nagar, Whitefield" value={locality}
          onChange={e => setLocality(e.target.value)}
          className="border-white/10 bg-white/5 text-sm text-white h-9" />
      </FilterSection>

      {/* Qualification */}
      <FilterSection title="My Qualification">
        <Select value={education} onValueChange={(v) => setEducation(v ?? "all")}>
          <SelectTrigger className="border-white/10 bg-white/5 text-sm h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Show all jobs</SelectItem>
            {EDUCATION_OPTIONS.filter(o => o.value !== "any").map(o => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="mt-1.5 text-[11px] text-[#64748B]">Shows jobs open to your qualification level.</p>
      </FilterSection>

      {/* Job Category / Role */}
      <FilterSection title="Job Category">
        <Select value={category} onValueChange={(v) => setCategory(v ?? "")}>
          <SelectTrigger className="border-white/10 bg-white/5 text-sm h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="max-h-64">
            {CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </FilterSection>

      {/* Experience Level */}
      <FilterSection title="Experience Level">
        <div className="space-y-2">
          {EXPERIENCE_OPTIONS.map(o => (
            <label key={o.value} className="flex cursor-pointer items-center gap-2">
              <input type="radio" name="exp" value={o.value} checked={experience === o.value}
                onChange={() => setExperience(o.value)}
                className="accent-[#3B82F6] h-3.5 w-3.5" />
              <span className={`text-sm ${experience === o.value ? "text-white font-medium" : "text-[#94A3B8]"}`}>{o.label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Employment Type */}
      <FilterSection title="Job Type">
        <div className="space-y-2">
          {EMPLOYMENT_TYPES.map(t => (
            <label key={t.value} className="flex cursor-pointer items-center gap-2">
              <Checkbox id={t.value} checked={employmentTypes.includes(t.value)}
                onCheckedChange={() => toggleEmploymentType(t.value)} />
              <span className={`text-sm ${employmentTypes.includes(t.value) ? "text-white" : "text-[#94A3B8]"}`}>{t.label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Salary Range */}
      <FilterSection title="Salary (₹ per month)">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {SALARY_PRESETS.map(p => (
              <button key={p.value} onClick={() => setSalaryMin(salaryMin === p.value ? 0 : p.value)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition-all ${
                  salaryMin === p.value ? "bg-[#10B981] text-white" : "border border-white/10 bg-white/5 text-[#94A3B8] hover:border-[#10B981]/50 hover:text-[#10B981]"
                }`}>
                {p.label}
              </button>
            ))}
          </div>
          {/* compact 2-up controls: fine on phones */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <p className="mb-1 text-[10px] text-[#64748B]">Min</p>
              <Input type="number" placeholder="e.g. 15000" value={salaryMin || ""}
                onChange={e => setSalaryMin(parseInt(e.target.value) || 0)}
                className="border-white/10 bg-white/5 text-xs text-white h-8" />
            </div>
            <div>
              <p className="mb-1 text-[10px] text-[#64748B]">Max</p>
              <Input type="number" placeholder="e.g. 50000" value={salaryMax || ""}
                onChange={e => setSalaryMax(parseInt(e.target.value) || 0)}
                className="border-white/10 bg-white/5 text-xs text-white h-8" />
            </div>
          </div>
        </div>
      </FilterSection>

      {/* Skills */}
      <FilterSection title="Skills" defaultOpen={false}>
        <div className="flex flex-wrap gap-1.5">
          {SKILL_TAGS.map(s => (
            <button key={s} onClick={() => toggleSkill(s)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition-all ${
                activeSkillTags.includes(s)
                  ? "bg-[#8B5CF6] text-white"
                  : "border border-white/10 bg-white/5 text-[#94A3B8] hover:border-[#8B5CF6]/50 hover:text-[#8B5CF6]"
              }`}>
              {s}
            </button>
          ))}
        </div>
      </FilterSection>

      {/* Remote + External toggles */}
      <FilterSection title="More Options" defaultOpen={false}>
        <div className="space-y-2.5">
          <label className="flex cursor-pointer items-center gap-2">
            <Checkbox id="remote" checked={remoteOnly} onCheckedChange={v => setRemoteOnly(v === true)} />
            <span className="text-sm text-[#94A3B8]">Remote only</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <Checkbox id="ext" checked={showExternal} onCheckedChange={v => setShowExternal(v === true)} />
            <span className="text-sm text-[#94A3B8]">Include live listings</span>
          </label>
        </div>
      </FilterSection>

      <Button onClick={fetchJobs} className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
        <Search className="mr-2 h-4 w-4" /> Search
      </Button>
    </div>
  );

  return (
    <div className="pb-24">
      {/* Hero Search Bar */}
      <section className="hero-glow border-b border-white/10 py-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading align="left" eyebrow="Job Search"
            title="Find Your Perfect Role"
            description="Smart filters · 25+ verified jobs · Live listings from top companies across India"
            className="mb-6" />

          <div className="glass-card flex flex-col gap-2 p-2 sm:flex-row sm:items-center">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#94A3B8]" />
              <Input placeholder="Job title, skills, company..."
                value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && fetchJobs()}
                className="border-0 bg-transparent pl-9 text-white h-10" />
            </div>
            {/* City quick select */}
            <div className="relative w-44">
              <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#94A3B8] z-10 pointer-events-none" />
              <Select value={city} onValueChange={(v) => setCity(v ?? "")}>
                <SelectTrigger className="border-0 bg-white/5 pl-9 text-sm h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-64">
                  {CITIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {/* Category quick select */}
            <div className="relative w-52">
              <Briefcase className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#94A3B8] z-10 pointer-events-none" />
              <Select value={category} onValueChange={(v) => setCategory(v ?? "")}>
                <SelectTrigger className="border-0 bg-white/5 pl-9 text-sm h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-64">
                  {CATEGORIES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={fetchJobs} disabled={loading}
              className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] flex-shrink-0 h-10 px-6">
              {loading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Search
            </Button>
          </div>

          {/* Popular skill quick filters */}
          <div className="mt-3 flex flex-wrap gap-2">
            {SKILL_TAGS.map(tag => (
              <button key={tag} onClick={() => toggleSkill(tag)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
                  activeSkillTags.includes(tag)
                    ? "bg-[#3B82F6] text-white shadow-lg shadow-[#3B82F6]/20"
                    : "border border-white/10 bg-white/5 text-[#94A3B8] hover:border-[#3B82F6]/40 hover:text-[#3B82F6]"
                }`}>
                {tag}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex gap-8">
          {/* Desktop sidebar */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="glass-card sticky top-24 p-5 space-y-4 max-h-[calc(100vh-7rem)] overflow-y-auto">
              <FilterPanel />
            </div>
          </aside>

          {/* Results */}
          <div className="flex-1 min-w-0">
            {/* Active filters + sort bar */}
            <div className="mb-5 flex flex-wrap items-center gap-3">
              {/* Mobile filter button */}
              <Button onClick={() => setShowMobileFilters(true)} size="sm" variant="outline"
                className="lg:hidden border-white/10 bg-white/5">
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                Filters {activeFilterCount > 0 && <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#3B82F6] text-[10px] text-white">{activeFilterCount}</span>}
              </Button>

              {/* Results count */}
              <p className="text-sm text-[#94A3B8] mr-auto">
                <span className="font-semibold text-white">{totalShown}</span> jobs
                {showExternal && externalJobs.length > 0 && <span className="text-xs text-[#64748B]"> (incl. {externalJobs.length} live)</span>}
              </p>

              {/* Sort */}
              <div className="flex items-center gap-2">
                <ArrowUpDown className="h-4 w-4 text-[#64748B]" />
                <Select value={sortBy} onValueChange={(v) => setSortBy(v ?? "")}>
                  <SelectTrigger className="h-8 border-white/10 bg-white/5 text-xs w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SORT_OPTIONS.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Active filter chips */}
            {activeFilterCount > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {city !== "All Cities" && <FilterChip label={`City: ${city}`} onRemove={() => setCity("All Cities")} />}
                {category !== "all" && <FilterChip label={`Role: ${CATEGORIES.find(c => c.value === category)?.label}`} onRemove={() => setCategory("all")} />}
                {experience !== "all" && <FilterChip label={`Exp: ${EXPERIENCE_OPTIONS.find(e => e.value === experience)?.label}`} onRemove={() => setExperience("all")} />}
                {employmentTypes.map(t => <FilterChip key={t} label={EMPLOYMENT_TYPES.find(x => x.value === t)?.label || t} onRemove={() => toggleEmploymentType(t)} />)}
                {locality.trim() && <FilterChip label={`Area: ${locality.trim()}`} onRemove={() => setLocality("")} />}
                {education !== "all" && <FilterChip label={`Qualification: ${EDUCATION_OPTIONS.find(o => o.value === education)?.label}`} onRemove={() => setEducation("all")} />}
                {salaryMin > 0 && <FilterChip label={`Min ₹${salaryMin.toLocaleString("en-IN")}/month`} onRemove={() => setSalaryMin(0)} />}
                {salaryMax > 0 && <FilterChip label={`Max ₹${salaryMax.toLocaleString("en-IN")}/month`} onRemove={() => setSalaryMax(0)} />}
                {remoteOnly && <FilterChip label="Remote Only" onRemove={() => setRemoteOnly(false)} />}
                {activeSkillTags.map(s => <FilterChip key={s} label={s} onRemove={() => toggleSkill(s)} />)}
              </div>
            )}

            {/* AI Recommendations */}
            {recommendedJobs.length > 0 && (
              <div className="mb-8">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[#8B5CF6]" />
                  <h2 className="font-semibold text-white">AI Picks for You</h2>
                  <Badge className="border-0 bg-[#8B5CF6]/20 text-[#8B5CF6] text-xs">Personalised</Badge>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {recommendedJobs.slice(0, 4).map((job, i) => <JobCard key={`rec-${job.id}`} job={job} index={i} />)}
                </div>
                <Separator className="mt-6 bg-white/10" />
              </div>
            )}

            {/* Job grid */}
            {loading ? (
              <div className="grid gap-5 sm:grid-cols-2">
                {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-2xl" />)}
              </div>
            ) : (
              <>
                <motion.div layout className="grid gap-5 sm:grid-cols-2">
                  {filteredJobs.map((job, i) => <JobCard key={`int-${job.id}`} job={job} index={i} />)}
                </motion.div>

                {/* External live jobs */}
                {showExternal && externalJobs.length > 0 && (
                  <div className="mt-8">
                    <div className="mb-4 flex items-center gap-2">
                      <ExternalLink className="h-4 w-4 text-[#06B6D4]" />
                      <h2 className="font-semibold text-white">Live Jobs</h2>
                      <Badge className="border-0 bg-[#06B6D4]/20 text-[#06B6D4] text-xs">External · Adzuna</Badge>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {externalJobs.map(job => (
                        <a key={job.id} href={job.redirect_url} target="_blank" rel="noopener noreferrer"
                          className="glass-card group block p-4 hover:border-[#06B6D4]/30 transition-all">
                          <div className="flex items-start gap-3">
                            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#06B6D4]/15 text-sm font-bold text-[#06B6D4]">
                              {job.company[0]}
                            </div>
                            <div className="min-w-0 flex-1">
                              <h3 className="font-semibold text-white line-clamp-1 group-hover:text-[#06B6D4] text-sm">{job.title}</h3>
                              <p className="text-xs text-[#94A3B8]">{job.company}</p>
                              <div className="mt-1 flex items-center gap-3 text-xs text-[#64748B]">
                                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>
                                {job.employment_type && <span className="capitalize">{job.employment_type.replace("_", " ")}</span>}
                              </div>
                              {(job.salary_min || job.salary_max) && (
                                <p className="mt-1 text-xs font-medium text-[#10B981]">
                                  {job.salary_min ? `₹${(job.salary_min/100000).toFixed(0)}L` : ""}
                                  {job.salary_min && job.salary_max ? " – " : ""}
                                  {job.salary_max ? `₹${(job.salary_max/100000).toFixed(0)}L` : ""}
                                </p>
                              )}
                            </div>
                            <ExternalLink className="h-4 w-4 text-[#64748B] flex-shrink-0" />
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty state */}
                {totalShown === 0 && (
                  <div className="glass-card p-12 text-center">
                    <Search className="mx-auto mb-3 h-10 w-10 text-[#64748B]" />
                    <p className="text-white font-semibold mb-1">No jobs match your filters</p>
                    <p className="text-sm text-[#94A3B8] mb-4">Try adjusting your city, role, or salary range</p>
                    <Button onClick={clearFilters} variant="outline" className="border-white/10">Clear All Filters</Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile filter drawer */}
      <AnimatePresence>
        {showMobileFilters && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setShowMobileFilters(false)} />
            <motion.div initial={{ x: "-100%" }} animate={{ x: 0 }} exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 30 }}
              className="fixed inset-y-0 left-0 z-50 w-80 overflow-y-auto bg-[#0F172A] border-r border-white/10 p-5 lg:hidden">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-semibold text-white">Filters</h2>
                <button onClick={() => setShowMobileFilters(false)} className="rounded-lg p-1.5 text-[#94A3B8] hover:bg-white/10 hover:text-white">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <FilterPanel />
              <div className="mt-4 pb-8">
                <Button onClick={() => setShowMobileFilters(false)} className="w-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                  Show {filteredJobs.length} Jobs
                </Button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
