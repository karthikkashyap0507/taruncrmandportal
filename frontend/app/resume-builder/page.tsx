"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Award, BookOpen, Briefcase, Download, Eye, FileText, Layers, Plus, Save, Sparkles, Trash2, User, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { profilesApi, apiError } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { useAuthStore } from "@/store/auth-store";

type Template = "modern" | "classic" | "executive";

interface ResumeData {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  website: string;
  summary: string;
  skills: string[];
  experience: { company: string; role: string; startDate: string; endDate: string; current: boolean; description: string }[];
  education: { school: string; degree: string; field: string; startDate: string; endDate: string; gpa: string }[];
  projects: { name: string; description: string; url: string; tech: string }[];
  certifications: { name: string; issuer: string; date: string; url: string }[];
}

const EMPTY_RESUME: ResumeData = {
  name: "", email: "", phone: "", location: "", linkedin: "", website: "",
  summary: "", skills: [],
  experience: [], education: [], projects: [], certifications: [],
};

export default function ResumeBuilderPage() {
  const router = useRouter();
  const { user, hydrated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [template, setTemplate] = useState<Template>("modern");
  const [activeTab, setActiveTab] = useState("personal");
  const [resumeData, setResumeData] = useState<ResumeData>(EMPTY_RESUME);
  const [newSkill, setNewSkill] = useState("");
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hydrated) return;
    loadData();
  }, [hydrated]);

  const loadData = async () => {
    try {
      const [meRes, profileRes] = await Promise.all([
        fetchMe().catch(() => null),
        profilesApi.getCandidateProfile().catch(() => null),
      ]);
      const me = meRes as any;
      const profile = profileRes?.data as any;
      setResumeData({
        ...EMPTY_RESUME,
        name: me?.name || "",
        email: me?.email || "",
        summary: profile?.headline || "",
        skills: profile?.skills || [],
        experience: (profile?.experience || []).map((e: any) => ({ ...e, current: false })),
      });
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const update = (field: keyof ResumeData, value: any) =>
    setResumeData((d) => ({ ...d, [field]: value }));

  const addSkill = () => {
    if (newSkill.trim() && !resumeData.skills.includes(newSkill.trim())) {
      update("skills", [...resumeData.skills, newSkill.trim()]);
      setNewSkill("");
    }
  };

  const handlePrint = () => {
    if (!printRef.current) return;
    const content = printRef.current.outerHTML;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`<!DOCTYPE html><html><head><title>${resumeData.name || "Resume"} - Resume</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Segoe UI', Arial, sans-serif; background: white; color: #1a1a1a; }
      @page { margin: 0.5in; size: A4; }
    </style></head><body>${content}</body></html>`);
    win.document.close();
    setTimeout(() => { win.print(); win.close(); }, 500);
  };

  const saveToProfile = async () => {
    setSaving(true);
    try {
      await profilesApi.updateCandidateProfile({
        headline: resumeData.summary,
        skills: resumeData.skills,
        experience: resumeData.experience,
      });
      alert("Saved to profile!");
    } catch (e) { alert(apiError(e, "Failed to save")); }
    finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-[#3B82F6] border-t-transparent" />
          <p className="text-[#94A3B8]">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-24 pt-8">
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-3xl font-bold text-white flex items-center gap-3">
              <FileText className="h-8 w-8 text-[#3B82F6]" />
              Resume Builder
            </h1>
            <p className="mt-1 text-[#94A3B8]">Create a professional resume in minutes. Choose a template, fill in your details, download as PDF.</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" onClick={saveToProfile} disabled={saving} className="border-white/10 bg-white/5">
              <Save className="mr-2 h-4 w-4" />
              {saving ? "Saving..." : "Save to Profile"}
            </Button>
            <Button variant="outline" onClick={handlePrint} className="border-white/10 bg-white/5">
              <Eye className="mr-2 h-4 w-4" />
              Preview
            </Button>
            <Button onClick={handlePrint} className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </Button>
          </div>
        </div>

        {/* Template Selector */}
        <div className="mb-6 glass-card p-4">
          <p className="mb-3 text-sm font-semibold text-white flex items-center gap-2"><Layers className="h-4 w-4 text-[#8B5CF6]" /> Choose Template</p>
          <div className="flex gap-3">
            {(["modern", "classic", "executive"] as Template[]).map((t) => (
              <button
                key={t}
                onClick={() => setTemplate(t)}
                className={`flex-1 rounded-xl border p-3 text-center text-sm font-medium capitalize transition-all ${
                  template === t
                    ? "border-[#3B82F6] bg-[#3B82F6]/10 text-[#3B82F6]"
                    : "border-white/10 bg-white/5 text-[#94A3B8] hover:border-white/30"
                }`}
              >
                {t === "modern" && "⚡ Modern"}
                {t === "classic" && "📄 Classic"}
                {t === "executive" && "👔 Executive"}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-8 xl:grid-cols-2">
          {/* Editor */}
          <div>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-4 grid w-full grid-cols-5 bg-white/5 border border-white/10">
                <TabsTrigger value="personal"><User className="h-3.5 w-3.5" /></TabsTrigger>
                <TabsTrigger value="experience"><Briefcase className="h-3.5 w-3.5" /></TabsTrigger>
                <TabsTrigger value="education"><BookOpen className="h-3.5 w-3.5" /></TabsTrigger>
                <TabsTrigger value="skills"><Sparkles className="h-3.5 w-3.5" /></TabsTrigger>
                <TabsTrigger value="extras"><Award className="h-3.5 w-3.5" /></TabsTrigger>
              </TabsList>

              {/* Personal Info */}
              <TabsContent value="personal" className="space-y-4">
                <Card className="bg-white/5 border-white/10">
                  <CardHeader><CardTitle className="text-white text-lg">Personal Information</CardTitle></CardHeader>
                  <CardContent className="grid gap-4 sm:grid-cols-2">
                    {[
                      { label: "Full Name", key: "name", placeholder: "John Doe" },
                      { label: "Email", key: "email", placeholder: "john@example.com" },
                      { label: "Phone", key: "phone", placeholder: "+91 98765 43210" },
                      { label: "Location", key: "location", placeholder: "Bengaluru, Karnataka" },
                      { label: "LinkedIn URL", key: "linkedin", placeholder: "linkedin.com/in/johndoe" },
                      { label: "Portfolio / Website", key: "website", placeholder: "johndoe.dev" },
                    ].map(({ label, key, placeholder }) => (
                      <div key={key} className="space-y-1.5">
                        <Label className="text-[#94A3B8] text-xs">{label}</Label>
                        <Input
                          placeholder={placeholder}
                          value={(resumeData as any)[key]}
                          onChange={(e) => update(key as keyof ResumeData, e.target.value)}
                          className="border-white/10 bg-white/5 text-white text-sm"
                        />
                      </div>
                    ))}
                    <div className="space-y-1.5 sm:col-span-2">
                      <Label className="text-[#94A3B8] text-xs">Professional Summary</Label>
                      <Textarea
                        placeholder="A results-driven software engineer with 5+ years building scalable web applications..."
                        value={resumeData.summary}
                        onChange={(e) => update("summary", e.target.value)}
                        className="border-white/10 bg-white/5 text-white text-sm min-h-[100px]"
                      />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Experience */}
              <TabsContent value="experience" className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-white font-semibold">Work Experience</h3>
                  <Button size="sm" onClick={() => update("experience", [...resumeData.experience, { company: "", role: "", startDate: "", endDate: "", current: false, description: "" }])}
                    className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                    <Plus className="mr-1 h-4 w-4" /> Add
                  </Button>
                </div>
                {resumeData.experience.map((exp, i) => (
                  <Card key={i} className="bg-white/5 border-white/10">
                    <CardContent className="pt-4 space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-[#94A3B8]">Experience {i + 1}</span>
                        <button onClick={() => update("experience", resumeData.experience.filter((_, idx) => idx !== i))}
                          className="text-red-400 hover:text-red-300"><Trash2 className="h-4 w-4" /></button>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {[
                          { label: "Company", key: "company" },
                          { label: "Job Title", key: "role" },
                          { label: "Start Date", key: "startDate", type: "month" },
                          { label: "End Date", key: "endDate", type: "month" },
                        ].map(({ label, key, type }) => (
                          <div key={key} className="space-y-1">
                            <Label className="text-[#94A3B8] text-xs">{label}</Label>
                            <Input type={type || "text"} value={(exp as any)[key]}
                              onChange={(e) => { const arr = [...resumeData.experience]; arr[i] = { ...arr[i], [key]: e.target.value }; update("experience", arr); }}
                              className="border-white/10 bg-white/5 text-white text-sm" />
                          </div>
                        ))}
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[#94A3B8] text-xs">Key Achievements & Responsibilities</Label>
                        <Textarea value={exp.description}
                          onChange={(e) => { const arr = [...resumeData.experience]; arr[i] = { ...arr[i], description: e.target.value }; update("experience", arr); }}
                          placeholder="• Led a team of 5 engineers to deliver a microservices migration&#10;• Improved API response time by 40% through caching&#10;• Shipped 3 major features used by 1M+ users"
                          className="border-white/10 bg-white/5 text-white text-sm min-h-[100px]" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {resumeData.experience.length === 0 && (
                  <div className="glass-card p-8 text-center text-[#94A3B8]">
                    <Briefcase className="mx-auto mb-2 h-8 w-8 opacity-50" />
                    <p className="text-sm">Add your work experience to get started</p>
                  </div>
                )}
              </TabsContent>

              {/* Education */}
              <TabsContent value="education" className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-white font-semibold">Education</h3>
                  <Button size="sm" onClick={() => update("education", [...resumeData.education, { school: "", degree: "", field: "", startDate: "", endDate: "", gpa: "" }])}
                    className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                    <Plus className="mr-1 h-4 w-4" /> Add
                  </Button>
                </div>
                {resumeData.education.map((edu, i) => (
                  <Card key={i} className="bg-white/5 border-white/10">
                    <CardContent className="pt-4 space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-[#94A3B8]">Education {i + 1}</span>
                        <button onClick={() => update("education", resumeData.education.filter((_, idx) => idx !== i))}
                          className="text-red-400 hover:text-red-300"><Trash2 className="h-4 w-4" /></button>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {[
                          { label: "School / University", key: "school" },
                          { label: "Degree", key: "degree", placeholder: "B.Tech, M.S., MBA" },
                          { label: "Field of Study", key: "field", placeholder: "Computer Science" },
                          { label: "GPA / Percentage", key: "gpa", placeholder: "9.0 / 10 or 92%" },
                          { label: "Start Year", key: "startDate", type: "month" },
                          { label: "End Year", key: "endDate", type: "month" },
                        ].map(({ label, key, type, placeholder }) => (
                          <div key={key} className="space-y-1">
                            <Label className="text-[#94A3B8] text-xs">{label}</Label>
                            <Input type={type || "text"} placeholder={placeholder}
                              value={(edu as any)[key]}
                              onChange={(e) => { const arr = [...resumeData.education]; arr[i] = { ...arr[i], [key]: e.target.value }; update("education", arr); }}
                              className="border-white/10 bg-white/5 text-white text-sm" />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>

              {/* Skills */}
              <TabsContent value="skills" className="space-y-4">
                <Card className="bg-white/5 border-white/10">
                  <CardHeader><CardTitle className="text-white text-lg">Skills</CardTitle>
                    <CardDescription className="text-[#94A3B8]">Add technical skills, tools, languages</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Input placeholder="React, Python, AWS..." value={newSkill}
                        onChange={(e) => setNewSkill(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && addSkill()}
                        className="flex-1 border-white/10 bg-white/5 text-white" />
                      <Button onClick={addSkill} className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {resumeData.skills.map((skill, i) => (
                        <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-[#3B82F6]/20 border border-[#3B82F6]/30 px-3 py-1 text-sm text-[#3B82F6]">
                          {skill}
                          <button onClick={() => update("skills", resumeData.skills.filter((_, idx) => idx !== i))}
                            className="text-[#3B82F6]/60 hover:text-[#3B82F6]"><Trash2 className="h-3 w-3" /></button>
                        </span>
                      ))}
                    </div>
                    <div className="border-t border-white/10 pt-4">
                      <p className="mb-2 text-xs text-[#94A3B8]">Quick add popular skills:</p>
                      <div className="flex flex-wrap gap-2">
                        {["Python", "TypeScript", "React", "Node.js", "AWS", "Docker", "Kubernetes", "SQL", "Machine Learning", "System Design"].map((s) => (
                          <button key={s} onClick={() => { if (!resumeData.skills.includes(s)) update("skills", [...resumeData.skills, s]); }}
                            className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-[#94A3B8] hover:border-[#3B82F6] hover:text-[#3B82F6] transition-colors">
                            + {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Extras: Projects + Certifications */}
              <TabsContent value="extras" className="space-y-6">
                {/* Projects */}
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-white font-semibold">Projects</h3>
                    <Button size="sm" onClick={() => update("projects", [...resumeData.projects, { name: "", description: "", url: "", tech: "" }])}
                      className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                      <Plus className="mr-1 h-4 w-4" /> Add
                    </Button>
                  </div>
                  {resumeData.projects.map((proj, i) => (
                    <Card key={i} className="mb-3 bg-white/5 border-white/10">
                      <CardContent className="pt-4 space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-[#94A3B8]">Project {i + 1}</span>
                          <button onClick={() => update("projects", resumeData.projects.filter((_, idx) => idx !== i))}
                            className="text-red-400"><Trash2 className="h-4 w-4" /></button>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          {[{ label: "Project Name", key: "name" }, { label: "Live URL / GitHub", key: "url" }, { label: "Technologies Used", key: "tech" }].map(({ label, key }) => (
                            <div key={key} className="space-y-1">
                              <Label className="text-[#94A3B8] text-xs">{label}</Label>
                              <Input value={(proj as any)[key]}
                                onChange={(e) => { const arr = [...resumeData.projects]; arr[i] = { ...arr[i], [key]: e.target.value }; update("projects", arr); }}
                                className="border-white/10 bg-white/5 text-white text-sm" />
                            </div>
                          ))}
                        </div>
                        <div className="space-y-1">
                          <Label className="text-[#94A3B8] text-xs">Description</Label>
                          <Textarea value={proj.description}
                            onChange={(e) => { const arr = [...resumeData.projects]; arr[i] = { ...arr[i], description: e.target.value }; update("projects", arr); }}
                            className="border-white/10 bg-white/5 text-white text-sm min-h-[80px]" />
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Certifications */}
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-white font-semibold">Certifications</h3>
                    <Button size="sm" onClick={() => update("certifications", [...resumeData.certifications, { name: "", issuer: "", date: "", url: "" }])}
                      className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]">
                      <Plus className="mr-1 h-4 w-4" /> Add
                    </Button>
                  </div>
                  {resumeData.certifications.map((cert, i) => (
                    <Card key={i} className="mb-3 bg-white/5 border-white/10">
                      <CardContent className="pt-4 space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-[#94A3B8]">Certification {i + 1}</span>
                          <button onClick={() => update("certifications", resumeData.certifications.filter((_, idx) => idx !== i))}
                            className="text-red-400"><Trash2 className="h-4 w-4" /></button>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          {[{ label: "Certificate Name", key: "name" }, { label: "Issuing Organisation", key: "issuer" }, { label: "Date", key: "date", type: "month" }, { label: "Credential URL", key: "url" }].map(({ label, key, type }) => (
                            <div key={key} className="space-y-1">
                              <Label className="text-[#94A3B8] text-xs">{label}</Label>
                              <Input type={type} value={(cert as any)[key]}
                                onChange={(e) => { const arr = [...resumeData.certifications]; arr[i] = { ...arr[i], [key]: e.target.value }; update("certifications", arr); }}
                                className="border-white/10 bg-white/5 text-white text-sm" />
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Preview */}
          <div className="xl:sticky xl:top-24 xl:max-h-[calc(100vh-8rem)] xl:overflow-y-auto">
            <div className="mb-3 flex items-center gap-2">
              <Eye className="h-4 w-4 text-[#94A3B8]" />
              <span className="text-sm text-[#94A3B8]">Live Preview — what your PDF will look like</span>
            </div>
            <div ref={printRef} style={{ fontFamily: template === "modern" ? "'Segoe UI', sans-serif" : template === "classic" ? "Georgia, serif" : "'Segoe UI', sans-serif" }}
              className="bg-white text-slate-900 shadow-2xl rounded-lg overflow-hidden">
              {template === "modern" && <ModernTemplate data={resumeData} />}
              {template === "classic" && <ClassicTemplate data={resumeData} />}
              {template === "executive" && <ExecutiveTemplate data={resumeData} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModernTemplate({ data }: { data: ResumeData }) {
  return (
    <div style={{ padding: "0", minHeight: "297mm", background: "white" }}>
      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #1e3a8a 0%, #7c3aed 100%)", padding: "32px 40px", color: "white" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, margin: 0 }}>{data.name || "Your Name"}</h1>
        <p style={{ marginTop: "8px", fontSize: "14px", opacity: 0.85 }}>
          {[data.email, data.phone, data.location].filter(Boolean).join("  •  ")}
        </p>
        {(data.linkedin || data.website) && (
          <p style={{ marginTop: "4px", fontSize: "13px", opacity: 0.7 }}>
            {[data.linkedin, data.website].filter(Boolean).join("  •  ")}
          </p>
        )}
      </div>

      <div style={{ padding: "28px 40px" }}>
        {data.summary && (
          <Section title="Professional Summary" color="#1e3a8a">
            <p style={{ fontSize: "14px", lineHeight: 1.6, color: "#374151" }}>{data.summary}</p>
          </Section>
        )}

        {data.skills.length > 0 && (
          <Section title="Skills" color="#1e3a8a">
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {data.skills.map((s, i) => (
                <span key={i} style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "20px", padding: "3px 12px", fontSize: "12px", color: "#1d4ed8", fontWeight: 500 }}>{s}</span>
              ))}
            </div>
          </Section>
        )}

        {data.experience.length > 0 && (
          <Section title="Work Experience" color="#1e3a8a">
            {data.experience.map((exp, i) => (
              <div key={i} style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: "15px", color: "#111827" }}>{exp.role || "Job Title"}</p>
                    <p style={{ fontSize: "14px", color: "#4b5563", fontWeight: 500 }}>{exp.company || "Company"}</p>
                  </div>
                  <p style={{ fontSize: "12px", color: "#6b7280", whiteSpace: "nowrap" }}>{exp.startDate} — {exp.current ? "Present" : exp.endDate}</p>
                </div>
                {exp.description && (
                  <div style={{ marginTop: "8px" }}>
                    {exp.description.split("\n").map((line, li) => (
                      <p key={li} style={{ fontSize: "13px", color: "#374151", lineHeight: 1.5, marginBottom: "2px" }}>{line}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </Section>
        )}

        {data.education.length > 0 && (
          <Section title="Education" color="#1e3a8a">
            {data.education.map((edu, i) => (
              <div key={i} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: "14px" }}>{edu.school}</p>
                    <p style={{ fontSize: "13px", color: "#4b5563" }}>{[edu.degree, edu.field].filter(Boolean).join(", ")}{edu.gpa ? ` — ${edu.gpa}` : ""}</p>
                  </div>
                  <p style={{ fontSize: "12px", color: "#6b7280" }}>{edu.startDate} — {edu.endDate}</p>
                </div>
              </div>
            ))}
          </Section>
        )}

        {data.projects.length > 0 && (
          <Section title="Projects" color="#1e3a8a">
            {data.projects.map((p, i) => (
              <div key={i} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <p style={{ fontWeight: 700, fontSize: "14px" }}>{p.name}</p>
                  {p.url && <p style={{ fontSize: "12px", color: "#3b82f6" }}>{p.url}</p>}
                </div>
                {p.tech && <p style={{ fontSize: "12px", color: "#7c3aed", marginTop: "2px" }}>Tech: {p.tech}</p>}
                {p.description && <p style={{ fontSize: "13px", color: "#374151", marginTop: "4px" }}>{p.description}</p>}
              </div>
            ))}
          </Section>
        )}

        {data.certifications.length > 0 && (
          <Section title="Certifications" color="#1e3a8a">
            {data.certifications.map((c, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: "13px" }}>{c.name}</p>
                  <p style={{ fontSize: "12px", color: "#6b7280" }}>{c.issuer}</p>
                </div>
                <p style={{ fontSize: "12px", color: "#6b7280" }}>{c.date}</p>
              </div>
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}

function ClassicTemplate({ data }: { data: ResumeData }) {
  return (
    <div style={{ padding: "40px", minHeight: "297mm", background: "white", fontFamily: "Georgia, serif" }}>
      <div style={{ textAlign: "center", borderBottom: "2px solid #1a1a1a", paddingBottom: "20px", marginBottom: "24px" }}>
        <h1 style={{ fontSize: "32px", fontWeight: 700, letterSpacing: "3px", textTransform: "uppercase" }}>{data.name || "YOUR NAME"}</h1>
        <p style={{ marginTop: "8px", fontSize: "13px", color: "#4b5563" }}>
          {[data.email, data.phone, data.location, data.linkedin].filter(Boolean).join(" | ")}
        </p>
      </div>

      {data.summary && (
        <ClassicSection title="OBJECTIVE">
          <p style={{ fontSize: "13px", lineHeight: 1.7 }}>{data.summary}</p>
        </ClassicSection>
      )}
      {data.experience.length > 0 && (
        <ClassicSection title="EXPERIENCE">
          {data.experience.map((exp, i) => (
            <div key={i} style={{ marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 700, fontSize: "14px" }}>{exp.role}</span>
                <span style={{ fontSize: "13px", fontStyle: "italic" }}>{exp.startDate} – {exp.current ? "Present" : exp.endDate}</span>
              </div>
              <p style={{ fontSize: "13px", fontStyle: "italic", color: "#4b5563" }}>{exp.company}</p>
              {exp.description && <p style={{ marginTop: "6px", fontSize: "13px", lineHeight: 1.6 }}>{exp.description}</p>}
            </div>
          ))}
        </ClassicSection>
      )}
      {data.education.length > 0 && (
        <ClassicSection title="EDUCATION">
          {data.education.map((edu, i) => (
            <div key={i} style={{ marginBottom: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 700, fontSize: "14px" }}>{[edu.degree, edu.field].filter(Boolean).join(", ")}</span>
                <span style={{ fontSize: "13px" }}>{edu.startDate} – {edu.endDate}</span>
              </div>
              <p style={{ fontSize: "13px", fontStyle: "italic" }}>{edu.school}{edu.gpa ? ` — ${edu.gpa}` : ""}</p>
            </div>
          ))}
        </ClassicSection>
      )}
      {data.skills.length > 0 && (
        <ClassicSection title="SKILLS">
          <p style={{ fontSize: "13px", lineHeight: 1.7 }}>{data.skills.join(" • ")}</p>
        </ClassicSection>
      )}
    </div>
  );
}

function ExecutiveTemplate({ data }: { data: ResumeData }) {
  return (
    <div style={{ minHeight: "297mm", background: "white", display: "flex" }}>
      {/* Left sidebar */}
      <div style={{ width: "200px", flexShrink: 0, background: "#0f172a", padding: "32px 20px", color: "white" }}>
        <div style={{ width: "80px", height: "80px", borderRadius: "50%", background: "linear-gradient(135deg,#3b82f6,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px", fontWeight: 700, marginBottom: "16px" }}>
          {(data.name || "?")[0]}
        </div>
        <h2 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "4px", wordBreak: "break-word" }}>{data.name || "Your Name"}</h2>
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.2)", marginTop: "20px", paddingTop: "16px" }}>
          {data.email && <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "8px", wordBreak: "break-all" }}>{data.email}</p>}
          {data.phone && <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "8px" }}>{data.phone}</p>}
          {data.location && <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "8px" }}>{data.location}</p>}
          {data.linkedin && <p style={{ fontSize: "11px", color: "#60a5fa", marginBottom: "8px", wordBreak: "break-all" }}>{data.linkedin}</p>}
        </div>
        {data.skills.length > 0 && (
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.2)", marginTop: "20px", paddingTop: "16px" }}>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", color: "#3b82f6", marginBottom: "12px" }}>Skills</p>
            {data.skills.map((s, i) => (
              <div key={i} style={{ marginBottom: "6px" }}>
                <p style={{ fontSize: "11px", color: "#e2e8f0" }}>{s}</p>
                <div style={{ height: "3px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", marginTop: "2px" }}>
                  <div style={{ height: "100%", width: "80%", background: "linear-gradient(to right,#3b82f6,#8b5cf6)", borderRadius: "2px" }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, padding: "32px 32px" }}>
        {data.summary && (
          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", color: "#3b82f6", marginBottom: "8px" }}>Profile</p>
            <p style={{ fontSize: "13px", lineHeight: 1.7, color: "#374151" }}>{data.summary}</p>
          </div>
        )}
        {data.experience.length > 0 && (
          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", color: "#3b82f6", borderBottom: "2px solid #3b82f6", paddingBottom: "4px", marginBottom: "16px" }}>Experience</p>
            {data.experience.map((exp, i) => (
              <div key={i} style={{ marginBottom: "18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <p style={{ fontWeight: 700, fontSize: "14px" }}>{exp.role}</p>
                  <p style={{ fontSize: "12px", color: "#6b7280" }}>{exp.startDate} — {exp.current ? "Present" : exp.endDate}</p>
                </div>
                <p style={{ fontSize: "13px", color: "#3b82f6", fontWeight: 500 }}>{exp.company}</p>
                {exp.description && <p style={{ marginTop: "6px", fontSize: "13px", color: "#4b5563", lineHeight: 1.6 }}>{exp.description}</p>}
              </div>
            ))}
          </div>
        )}
        {data.education.length > 0 && (
          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", color: "#3b82f6", borderBottom: "2px solid #3b82f6", paddingBottom: "4px", marginBottom: "16px" }}>Education</p>
            {data.education.map((edu, i) => (
              <div key={i} style={{ marginBottom: "12px" }}>
                <p style={{ fontWeight: 700, fontSize: "14px" }}>{edu.school}</p>
                <p style={{ fontSize: "13px", color: "#4b5563" }}>{[edu.degree, edu.field].filter(Boolean).join(", ")}{edu.gpa ? ` — GPA: ${edu.gpa}` : ""}</p>
                <p style={{ fontSize: "12px", color: "#6b7280" }}>{edu.startDate} — {edu.endDate}</p>
              </div>
            ))}
          </div>
        )}
        {data.certifications.length > 0 && (
          <div>
            <p style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: "uppercase", color: "#3b82f6", borderBottom: "2px solid #3b82f6", paddingBottom: "4px", marginBottom: "16px" }}>Certifications</p>
            {data.certifications.map((c, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: "13px" }}>{c.name}</p>
                  <p style={{ fontSize: "12px", color: "#6b7280" }}>{c.issuer}</p>
                </div>
                <p style={{ fontSize: "12px", color: "#6b7280" }}>{c.date}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "24px" }}>
      <h2 style={{ fontSize: "13px", fontWeight: 700, letterSpacing: "1.5px", textTransform: "uppercase", color, borderBottom: `2px solid ${color}`, paddingBottom: "4px", marginBottom: "14px" }}>{title}</h2>
      {children}
    </div>
  );
}

function ClassicSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <h2 style={{ fontSize: "12px", fontWeight: 700, letterSpacing: "2px", borderBottom: "1px solid #1a1a1a", paddingBottom: "4px", marginBottom: "12px" }}>{title}</h2>
      {children}
    </div>
  );
}
