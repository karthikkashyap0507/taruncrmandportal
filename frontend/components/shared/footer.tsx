import { Globe, Mail, MessageCircle, Share2, Sparkles } from "lucide-react";
import Link from "next/link";
import { NAV_LINKS, SITE } from "@/lib/constants";

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#0F172A] pb-24 lg:pb-12">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <span className="font-heading text-lg font-bold">{SITE.name}</span>
            </Link>
            <p className="mt-4 text-sm text-[#94A3B8]">{SITE.tagline}</p>
            <div className="mt-4 flex gap-3">
              {[Share2, Globe, MessageCircle, Mail].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-[#94A3B8] transition-colors hover:border-[#3B82F6]/50 hover:text-white"
                  aria-label="Social link"
                >
                  <Icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-white">Quick Links</h4>
            <ul className="space-y-2">
              {NAV_LINKS.filter((l) => l.label !== "Sign In").map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-[#94A3B8] transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-white">For Employers</h4>
            <ul className="space-y-2 text-sm text-[#94A3B8]">
              <li>
                <Link href="/services" className="hover:text-white">
                  Post a Job
                </Link>
              </li>
              <li>
                <Link href="/services" className="hover:text-white">
                  Recruitment Services
                </Link>
              </li>
              <li>
                <Link href="/auth/signin" className="hover:text-white">
                  Recruiter Login
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-white">Contact</h4>
            <ul className="space-y-2 text-sm text-[#94A3B8]">
              <li>{SITE.email}</li>
              <li>{SITE.phone}</li>
              <li>{SITE.address}</li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 sm:flex-row">
          <p className="text-sm text-[#94A3B8]">
            © {new Date().getFullYear()} {SITE.name}. All rights reserved.
          </p>
          <div className="flex gap-6 text-sm text-[#94A3B8]">
            <Link href="#" className="hover:text-white">
              Privacy Policy
            </Link>
            <Link href="#" className="hover:text-white">
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
