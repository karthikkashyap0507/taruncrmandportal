// Same qualification levels the job portal uses, so synced jobs read the same in both apps
export const EDUCATION_OPTIONS: { value: string; label: string }[] = [
  { value: "any", label: "Any qualification" },
  { value: "10th", label: "10th pass" },
  { value: "12th", label: "12th pass" },
  { value: "iti", label: "ITI" },
  { value: "diploma", label: "Diploma" },
  { value: "graduate", label: "Graduate" },
  { value: "postgraduate", label: "Post-graduate" },
];

export function educationLabel(value?: string | null): string | null {
  return EDUCATION_OPTIONS.find(o => o.value === value)?.label ?? null;
}

/** "JP Nagar, Bengaluru" from a locality and a city. */
export function formatPlace(location?: string | null, locality?: string | null): string | null {
  const parts = [locality, location].filter(Boolean);
  return parts.length ? parts.join(", ") : null;
}

/** "₹18,000 – ₹25,000 / month" */
export function formatSalaryRange(min?: number | null, max?: number | null, period?: string | null): string | null {
  if (!min && !max) return null;
  const fmt = (n: number) => `₹${Number(n).toLocaleString("en-IN")}`;
  const range = min && max ? `${fmt(min)} – ${fmt(max)}` : min ? `${fmt(min)}+` : `Up to ${fmt(max!)}`;
  return period === "month" ? `${range} / month` : period === "year" ? `${range} / year` : range;
}
