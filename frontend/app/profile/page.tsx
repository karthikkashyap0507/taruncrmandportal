"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, Briefcase, FileText, Plus, Save, Trash2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { profilesApi, apiError } from "@/services/api";
import type { Candidate } from "@/types";

interface ExperienceItem {
  company: string;
  role: string;
  startDate: string;
  endDate: string;
  description: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [headline, setHeadline] = useState("");
  const [skillsInput, setSkillsInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [experience, setExperience] = useState<ExperienceItem[]>([]);
  const [resumeUrl, setResumeUrl] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await profilesApi.getCandidateProfile();
      const p = res.data;
      setProfile(p);
      setHeadline(p.headline || "");
      setSkills(p.skills || []);
      setExperience((p.experience || []) as ExperienceItem[]);
      setResumeUrl(p.resume_url || "");
    } catch (err) {
      console.error("Failed to load profile", err);
    } finally {
      setLoading(false);
    }
  };

  const addSkill = () => {
    if (skillsInput.trim() && !skills.includes(skillsInput.trim())) {
      setSkills([...skills, skillsInput.trim()]);
      setSkillsInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  const addExperience = () => {
    setExperience([
      ...experience,
      {
        company: "",
        role: "",
        startDate: "",
        endDate: "",
        description: "",
      },
    ]);
  };

  const updateExperience = (index: number, field: keyof ExperienceItem, value: string) => {
    const newExp = [...experience];
    newExp[index] = { ...newExp[index], [field]: value };
    setExperience(newExp);
  };

  const removeExperience = (index: number) => {
    setExperience(experience.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await profilesApi.updateCandidateProfile({
        headline,
        skills,
        experience,
        resume_url: resumeUrl,
      });
      alert("Profile saved successfully!");
    } catch (err) {
      alert(apiError(err, "Failed to save profile"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="pb-24 pt-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <Skeleton className="h-12 w-48 rounded-xl mb-8" />
          <div className="space-y-6">
            <Skeleton className="h-64 rounded-2xl" />
            <Skeleton className="h-80 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pb-24 pt-12">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="font-heading text-3xl font-bold text-white">My Profile</h1>
          <Button
            onClick={handleSave}
            disabled={saving}
            className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6]"
          >
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save Profile"}
          </Button>
        </div>

        <div className="space-y-6">
          {/* Basic Info */}
          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <User className="h-5 w-5 text-[#3B82F6]" />
                Professional Headline
              </CardTitle>
              <CardDescription className="text-[#94A3B8]">
                A short summary of your professional background
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                placeholder="e.g. Full Stack Developer with 5+ years of experience"
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                className="border-white/10 bg-white/5 text-white"
              />
            </CardContent>
          </Card>

          {/* Skills */}
          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-[#8B5CF6]" />
                Skills
              </CardTitle>
              <CardDescription className="text-[#94A3B8]">
                Add your technical and soft skills
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Add a skill..."
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addSkill()}
                  className="flex-1 border-white/10 bg-white/5 text-white"
                />
                <Button onClick={addSkill} variant="outline" className="border-white/10 bg-white/5">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {skills.map((skill, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm text-white"
                  >
                    {skill}
                    <button
                      onClick={() => removeSkill(skill)}
                      className="text-[#94A3B8] hover:text-white transition-colors"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Experience */}
          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Briefcase className="h-5 w-5 text-[#3B82F6]" />
                    Experience
                  </CardTitle>
                  <CardDescription className="text-[#94A3B8]">
                    Your work history
                  </CardDescription>
                </div>
                <Button
                  onClick={addExperience}
                  variant="outline"
                  className="border-white/10 bg-white/5"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {experience.map((exp, index) => (
                <div key={index} className="glass-card p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">Experience {index + 1}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeExperience(index)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-[#94A3B8]">Company</Label>
                      <Input
                        value={exp.company}
                        onChange={(e) => updateExperience(index, "company", e.target.value)}
                        className="border-white/10 bg-white/5 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-[#94A3B8]">Role</Label>
                      <Input
                        value={exp.role}
                        onChange={(e) => updateExperience(index, "role", e.target.value)}
                        className="border-white/10 bg-white/5 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-[#94A3B8]">Start Date</Label>
                      <Input
                        type="month"
                        value={exp.startDate}
                        onChange={(e) => updateExperience(index, "startDate", e.target.value)}
                        className="border-white/10 bg-white/5 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-[#94A3B8]">End Date</Label>
                      <Input
                        type="month"
                        value={exp.endDate}
                        onChange={(e) => updateExperience(index, "endDate", e.target.value)}
                        className="border-white/10 bg-white/5 text-white"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-[#94A3B8]">Description</Label>
                    <Textarea
                      value={exp.description}
                      onChange={(e) => updateExperience(index, "description", e.target.value)}
                      className="border-white/10 bg-white/5 text-white min-h-[100px]"
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Resume */}
          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#8B5CF6]" />
                Resume
              </CardTitle>
              <CardDescription className="text-[#94A3B8]">
                Link to your resume or CV
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Input
                placeholder="https://example.com/resume.pdf"
                value={resumeUrl}
                onChange={(e) => setResumeUrl(e.target.value)}
                className="border-white/10 bg-white/5 text-white"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
