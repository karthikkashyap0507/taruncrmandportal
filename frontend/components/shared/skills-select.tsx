"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Search, X, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export const SKILLS_BY_CATEGORY: Record<string, string[]> = {
  "Frontend":    ["React", "Next.js", "Vue.js", "Angular", "TypeScript", "JavaScript", "HTML/CSS", "Tailwind CSS", "Redux", "Svelte"],
  "Backend":     ["Node.js", "Python", "Java", "Go", "Django", "FastAPI", "Spring Boot", "Express.js", "PHP", "Ruby on Rails", "Rust", "C#"],
  "Mobile":      ["Flutter", "React Native", "Swift", "Kotlin", "Android", "iOS", "Dart"],
  "Database":    ["SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Firebase", "Cassandra", "DynamoDB"],
  "Cloud/DevOps":["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Jenkins", "Ansible", "Nginx"],
  "AI / ML":     ["Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "Data Science", "LLM", "OpenAI", "Langchain"],
  "Data":        ["Power BI", "Tableau", "Apache Spark", "Hadoop", "ETL", "Data Analytics", "Pandas", "NumPy", "Airflow"],
  "Security":    ["Cybersecurity", "VAPT", "Penetration Testing", "SOC", "SIEM", "Network Security", "ISO 27001"],
  "Design":      ["Figma", "Adobe XD", "UI/UX Design", "Sketch", "Prototyping", "Framer"],
  "Other":       ["Git", "REST API", "GraphQL", "Agile", "Scrum", "Product Management", "Blockchain", "Web3", "Salesforce"],
};

export const ALL_SKILLS = Object.values(SKILLS_BY_CATEGORY).flat();

interface SkillsSelectProps {
  selected: string[];
  onChange: (skills: string[]) => void;
  placeholder?: string;
  className?: string;
  maxVisible?: number;
}

export function SkillsSelect({
  selected,
  onChange,
  placeholder = "Search & select skills...",
  className,
  maxVisible = 3,
}: SkillsSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const toggle = (skill: string) => {
    onChange(selected.includes(skill) ? selected.filter(s => s !== skill) : [...selected, skill]);
  };

  const filteredCategories = Object.entries(SKILLS_BY_CATEGORY).reduce<Record<string, string[]>>(
    (acc, [cat, skills]) => {
      const matches = search
        ? skills.filter(s => s.toLowerCase().includes(search.toLowerCase()))
        : skills;
      if (matches.length) acc[cat] = matches;
      return acc;
    },
    {}
  );

  const visibleChips = selected.slice(0, maxVisible);
  const hiddenCount = selected.length - maxVisible;

  return (
    <div ref={ref} className={cn("relative", className)}>
      {/* Trigger */}
      <div
        onClick={() => setOpen(!open)}
        className={cn(
          "flex min-h-[2.5rem] cursor-pointer flex-wrap items-center gap-1.5 rounded-xl border px-3 py-2 transition-colors",
          open
            ? "border-[#1B75BB]/60 bg-[#0F1F35] ring-1 ring-[#1B75BB]/30"
            : "border-white/10 bg-white/5 hover:border-white/20"
        )}
      >
        {selected.length === 0 ? (
          <span className="text-sm text-[#64748B]">{placeholder}</span>
        ) : (
          <>
            {visibleChips.map(skill => (
              <span
                key={skill}
                className="flex items-center gap-1 rounded-full bg-[#1B75BB]/20 px-2 py-0.5 text-xs font-medium text-[#1B75BB]"
              >
                {skill}
                <button
                  type="button"
                  onClick={e => { e.stopPropagation(); toggle(skill); }}
                  className="hover:text-white"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            {hiddenCount > 0 && (
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-[#94A3B8]">
                +{hiddenCount} more
              </span>
            )}
          </>
        )}
        <ChevronDown className={cn("ml-auto h-4 w-4 flex-shrink-0 text-[#64748B] transition-transform", open && "rotate-180")} />
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-80 overflow-y-auto rounded-xl border border-white/10 bg-[#0F1F35] shadow-2xl shadow-black/50">
          {/* Search input */}
          <div className="sticky top-0 border-b border-white/10 bg-[#0F1F35] p-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#64748B]" />
              <input
                autoFocus
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search skills..."
                className="w-full rounded-lg bg-white/5 py-1.5 pl-8 pr-3 text-sm text-white outline-none placeholder:text-[#64748B] focus:ring-1 focus:ring-[#1B75BB]/40"
              />
            </div>
            {selected.length > 0 && (
              <button
                onClick={() => onChange([])}
                className="mt-1.5 text-xs text-[#94A3B8] hover:text-white"
              >
                Clear all ({selected.length})
              </button>
            )}
          </div>

          {/* Category groups */}
          <div className="p-2">
            {Object.entries(filteredCategories).length === 0 ? (
              <p className="py-6 text-center text-sm text-[#64748B]">No skills match "{search}"</p>
            ) : (
              Object.entries(filteredCategories).map(([category, skills]) => (
                <div key={category} className="mb-3">
                  <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-[#64748B]">
                    {category}
                  </p>
                  <div className="flex flex-wrap gap-1.5 px-1">
                    {skills.map(skill => {
                      const isSelected = selected.includes(skill);
                      return (
                        <button
                          key={skill}
                          type="button"
                          onClick={() => toggle(skill)}
                          className={cn(
                            "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-all",
                            isSelected
                              ? "bg-[#1B75BB] text-white"
                              : "border border-white/10 bg-white/5 text-[#94A3B8] hover:border-[#1B75BB]/40 hover:bg-[#1B75BB]/10 hover:text-[#1B75BB]"
                          )}
                        >
                          {isSelected && <Check className="h-3 w-3" />}
                          {skill}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
