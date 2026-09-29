export const SITE = {
  name: "JobsNexGen",
  tagline: "Connecting Talent with Opportunity",
  description:
    "JobsNexgen is a leading job platform dedicated to bridging the gap between talented professionals and forward-thinking companies. Founded in 2024, we provide secure, transparent, and AI-powered hiring.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  email: "support@jobsnexgen.in",
  phone: "+91 9590336978",
  address:
    "Newbridge Business Centre, Manyata Embassy Business Park, 11th Floor, N1 Block, Bengaluru, Karnataka 560045",
} as const;

export const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/jobs", label: "Jobs" },
  { href: "/about", label: "About Us" },
  { href: "/services", label: "Add On Services" },
  { href: "/contact", label: "Contact Us" },
  { href: "/auth/signin", label: "Sign In" },
] as const;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
