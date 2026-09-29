"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export default function RootPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  useEffect(() => {
    if (user) router.replace("/dashboard");
    else router.replace("/login");
  }, [user, router]);
  return null;
}
