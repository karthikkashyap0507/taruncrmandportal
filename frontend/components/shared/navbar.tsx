"use client";

import { motion } from "framer-motion";
import { LayoutDashboard, LogOut, Menu, FileText, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { NAV_LINKS, SITE } from "@/lib/constants";
import { dashboardPathForRole } from "@/lib/dashboard-path";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth-store";

/** Brand logo — matches the JobsNexGen tri-colour identity */
function BrandLogo() {
  return (
    <div className="flex items-center gap-2.5">
      {/* Emblem */}
      <div className="relative flex h-9 w-9 items-center justify-center">
        <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-9 w-9">
          <circle cx="20" cy="20" r="19" stroke="url(#ring)" strokeWidth="1.5"/>
          {/* Blue arc / person */}
          <path d="M20 4 C10 4, 4 12, 4 20" stroke="#1B75BB" strokeWidth="3" strokeLinecap="round"/>
          {/* Orange arc / chart */}
          <path d="M20 4 C30 4, 36 12, 36 20" stroke="#F7941D" strokeWidth="3" strokeLinecap="round"/>
          {/* Green arc / gear */}
          <path d="M4 20 C4 30, 12 36, 20 36" stroke="#39B54A" strokeWidth="3" strokeLinecap="round"/>
          {/* Bottom arc */}
          <path d="M36 20 C36 30, 28 36, 20 36" stroke="#1B75BB" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
          {/* Person head */}
          <circle cx="13" cy="12" r="3" fill="#1B75BB"/>
          {/* Chart bars */}
          <rect x="25" y="14" width="3" height="6" rx="1" fill="#F7941D"/>
          <rect x="29" y="11" width="3" height="9" rx="1" fill="#F7941D" opacity="0.8"/>
          {/* Gear dot */}
          <circle cx="14" cy="24" r="3.5" fill="none" stroke="#39B54A" strokeWidth="2"/>
          <circle cx="14" cy="24" r="1.5" fill="#39B54A"/>
          <defs>
            <linearGradient id="ring" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#1B75BB"/>
              <stop offset="50%" stopColor="#F7941D"/>
              <stop offset="100%" stopColor="#39B54A"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      {/* Brand name — tri-colour */}
      <span className="font-heading text-[17px] font-bold tracking-tight">
        <span style={{ color: "#1B75BB" }}>Jobs</span>
        <span style={{ color: "#F7941D" }}>Nex</span>
        <span style={{ color: "#39B54A" }}>Gen</span>
      </span>
    </div>
  );
}

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const logout = useAuthStore((s) => s.logout);

  const isCandidate = user?.role === "candidate";

  return (
  <>
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 z-50 w-full border-b border-white/10 bg-[#091626]/90 backdrop-blur-xl"
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/">
          <BrandLogo />
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => {
            const isActive = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            const isSignIn = link.label === "Sign In";

            if (isSignIn) {
              if (hydrated && user) {
                return (
                  <div key="auth" className="ml-2 flex items-center gap-2">
                    {isCandidate && (
                      <Link href="/profile">
                        <Button size="sm" variant="outline" className="border-white/10 bg-white/5">
                          <FileText className="mr-1 h-4 w-4" /> Profile
                        </Button>
                      </Link>
                    )}
                    {isCandidate && (
                      <Link href="/resume-builder">
                        <Button size="sm" variant="outline" className="border-white/10 bg-white/5">
                          <FileText className="mr-1 h-4 w-4" /> Resume Builder
                        </Button>
                      </Link>
                    )}
                    <Button size="sm" variant="outline" className="border-white/10 bg-white/5"
                      onClick={() => router.push(dashboardPathForRole(user.role))}>
                      <LayoutDashboard className="mr-1 h-4 w-4" /> Dashboard
                    </Button>
                    <Button size="sm" variant="outline" className="border-white/10"
                      onClick={() => { logout(); router.push("/"); }}>
                      <LogOut className="mr-1 h-4 w-4" /> Sign out
                    </Button>
                  </div>
                );
              }
              return (
                <Link key={link.href} href={link.href} className="ml-2">
                  <Button size="sm" className="bg-gradient-to-r from-[#1B75BB] to-[#F7941D] hover:opacity-90 shadow-lg shadow-[#1B75BB]/20">
                    {link.label}
                  </Button>
                </Link>
              );
            }

            return (
              <Link key={link.href} href={link.href} prefetch={true}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-[#1B75BB]/15 text-[#1B75BB]" : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
                )}>
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile hamburger */}
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger
            className="lg:hidden inline-flex h-8 w-8 items-center justify-center rounded-lg text-white hover:bg-white/10"
            aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </SheetTrigger>
          <SheetContent side="right" className="w-full border-white/10 bg-[#091626] sm:max-w-sm">
            <div className="flex items-center justify-between">
              <BrandLogo />
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="mt-8 flex flex-col gap-2">
              {NAV_LINKS.map((link) => (
                <Link key={link.href} href={link.href} prefetch={true} onClick={() => setOpen(false)}
                  className={cn(
                    "rounded-xl px-4 py-3 text-base font-medium transition-colors",
                    pathname === link.href || pathname.startsWith(link.href)
                      ? "bg-[#1B75BB]/15 text-[#1B75BB]"
                      : "text-[#94A3B8] hover:bg-white/5"
                  )}>
                  {link.label}
                </Link>
              ))}
              {hydrated && user ? (
                <>
                  {isCandidate && (
                    <Link href="/profile" onClick={() => setOpen(false)}
                      className="rounded-xl px-4 py-3 text-base font-medium text-[#94A3B8] hover:text-white">Profile</Link>
                  )}
                  {isCandidate && (
                    <Link href="/resume-builder" onClick={() => setOpen(false)}
                      className="rounded-xl px-4 py-3 text-base font-medium text-[#94A3B8] hover:text-white">Resume Builder</Link>
                  )}
                  <Link href={dashboardPathForRole(user.role)} onClick={() => setOpen(false)}
                    className="rounded-xl px-4 py-3 text-base font-medium text-[#1B75BB]">Dashboard</Link>
                  <button type="button" onClick={() => { logout(); setOpen(false); router.push("/"); }}
                    className="rounded-xl px-4 py-3 text-left text-base font-medium text-[#94A3B8]">Sign out</button>
                </>
              ) : null}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </motion.header>

    {/* Mobile bottom tab bar */}
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/10 bg-[#091626]/95 backdrop-blur-xl lg:hidden">
      <div className="flex items-center justify-around px-2 py-2">
        {NAV_LINKS.filter((l) => l.label !== "Sign In").map((link) => {
          const isActive = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link key={link.href} href={link.href} prefetch={true}
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 text-[10px] font-medium",
                isActive ? "text-[#F7941D]" : "text-[#94A3B8]"
              )}>
              <span className={cn("h-1 w-1 rounded-full", isActive ? "bg-[#F7941D]" : "bg-transparent")} />
              {link.label.split(" ")[0]}
            </Link>
          );
        })}
        {hydrated && user ? (
          <Link href={dashboardPathForRole(user.role)}
            className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 text-[10px] font-medium text-[#F7941D]">
            <span className="h-1 w-1 rounded-full bg-[#F7941D]" />
            Dashboard
          </Link>
        ) : (
          <Link href="/auth/signin"
            className={cn(
              "flex flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 text-[10px] font-medium",
              pathname.startsWith("/auth") ? "text-[#F7941D]" : "text-[#94A3B8]"
            )}>Sign In</Link>
        )}
      </div>
    </nav>
  </>
  );
}
