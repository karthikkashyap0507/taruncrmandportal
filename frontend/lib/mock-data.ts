import type { Company, Service, Stat, Testimonial } from "@/types";

export const PLATFORM_STATS: Stat[] = [
  { label: "Active Jobs", value: 125000, suffix: "+" },
  { label: "Companies", value: 8500, suffix: "+" },
  { label: "Candidates Hired", value: 420000, suffix: "+" },
  { label: "AI Matches Daily", value: 95000, suffix: "+" },
];

export const FEATURED_COMPANIES: Company[] = [
  { id: 1, name: "NexTech Labs", industry: "AI & Technology", openPositions: 42 },
  { id: 2, name: "PixelFlow", industry: "Design & SaaS", openPositions: 18 },
  { id: 3, name: "CloudScale", industry: "Cloud Infrastructure", openPositions: 31 },
  { id: 4, name: "InsightAI", industry: "Data & Analytics", openPositions: 24 },
  { id: 5, name: "GrowthHive", industry: "Marketing", openPositions: 12 },
  { id: 6, name: "FinEdge", industry: "Fintech", openPositions: 27 },
];

export const TESTIMONIALS: Testimonial[] = [
  {
    id: 1,
    name: "Priya Sharma",
    role: "Software Engineer",
    company: "NexTech Labs",
    quote:
      "JobsNexGen matched me with my dream role in 2 weeks. The AI resume scoring helped me stand out instantly.",
    rating: 5,
  },
  {
    id: 2,
    name: "Rahul Mehta",
    role: "HR Director",
    company: "CloudScale",
    quote:
      "Our hiring pipeline is 3x faster. AI candidate ranking and ATS tools are game-changers for our team.",
    rating: 5,
  },
  {
    id: 3,
    name: "Ananya Reddy",
    role: "Product Designer",
    company: "PixelFlow",
    quote:
      "The career coach and mock interviews prepared me perfectly. Best job platform experience I've had.",
    rating: 5,
  },
];

export const JOB_CATEGORIES = [
  "Technology",
  "Design",
  "Marketing",
  "Sales",
  "Finance",
  "Healthcare",
  "Remote",
  "AI & ML",
];

export const ADDON_SERVICES: Service[] = [
  {
    id: 1,
    title: "AI Resume Building",
    description: "Create ATS-optimized resumes with AI in minutes.",
    price: "₹999",
    features: ["AI templates", "ATS scoring", "PDF export", "Unlimited edits"],
  },
  {
    id: 2,
    title: "Resume Optimization",
    description: "Boost your resume score with expert AI feedback.",
    price: "₹1,499",
    features: ["Keyword optimization", "Skill gap analysis", "Industry benchmarks"],
    popular: true,
  },
  {
    id: 3,
    title: "AI Career Coaching",
    description: "Personalized career roadmap and growth insights.",
    price: "₹2,999",
    features: ["1-on-1 sessions", "Skill roadmap", "Interview prep", "Salary insights"],
  },
  {
    id: 4,
    title: "Mock Interviews",
    description: "AI-powered mock interviews with real-time feedback.",
    price: "₹1,999",
    features: ["Voice interviews", "Technical rounds", "Communication score"],
  },
  {
    id: 5,
    title: "Premium Job Boosting",
    description: "Get your profile seen by top recruiters first.",
    price: "₹3,499",
    features: ["Featured listing", "Priority apply", "Recruiter alerts"],
  },
  {
    id: 6,
    title: "Recruitment Services",
    description: "End-to-end hiring support for enterprises.",
    price: "Custom",
    features: ["Dedicated recruiter", "Bulk hiring", "Analytics dashboard"],
  },
];

export const FAQ_ITEMS = [
  {
    q: "How does AI job matching work?",
    a: "We use semantic embeddings to match your skills, experience, and preferences with relevant roles in real time.",
  },
  {
    q: "Is JobsNexGen free for candidates?",
    a: "Yes! Basic job search, applications, and profile creation are free. Premium add-on services are optional.",
  },
  {
    q: "Can recruiters post jobs for free?",
    a: "Recruiters can start with a free plan. Pro and Enterprise plans unlock AI hiring tools and featured listings.",
  },
  {
    q: "How secure is my resume data?",
    a: "All data is encrypted, stored securely, and never shared without your consent. We follow enterprise-grade security standards.",
  },
];
