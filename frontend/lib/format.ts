export function formatSalary(min?: number | null, max?: number | null, period?: string | null): string {
  if (!min && !max) return "Competitive";
  const fmt = (n: number) => {
    if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
    return `₹${n.toLocaleString("en-IN")}`;
  };
  const per = period === "month" ? "/month" : period === "year" ? "/year" : "";
  if (min && max) return `${fmt(min)} - ${fmt(max)}${per}`;
  if (min) return `${fmt(min)}+${per}`;
  return `Up to ${fmt(max!)}${per}`;
}

export function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return n.toString();
}

// Minimum qualification options for jobs and applications
export const EDUCATION_OPTIONS: { value: string; label: string }[] = [
  { value: "any", label: "Any qualification" },
  { value: "10th", label: "10th pass" },
  { value: "12th", label: "12th pass" },
  { value: "iti", label: "ITI" },
  { value: "diploma", label: "Diploma" },
  { value: "graduate", label: "Graduate" },
  { value: "postgraduate", label: "Post-graduate" },
];

export function educationLabel(value?: string | null): string | undefined {
  return EDUCATION_OPTIONS.find(o => o.value === value)?.label;
}

/** "JP Nagar, Bengaluru" from a job's locality and city. */
export function formatPlace(location?: string | null, locality?: string | null): string | undefined {
  const parts = [locality, location].filter(Boolean);
  return parts.length ? parts.join(", ") : undefined;
}
