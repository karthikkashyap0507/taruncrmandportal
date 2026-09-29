import type { UserRole } from "@/types";

const ACCESS = "jobsnexgen_access_token";
const REFRESH = "jobsnexgen_refresh_token";
const USER = "jobsnexgen_user";

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  role: UserRole;
};

export type AuthSuccess = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

export function persistAuth(data: AuthSuccess): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS, data.access_token);
  localStorage.setItem(REFRESH, data.refresh_token);
  localStorage.setItem(USER, JSON.stringify(data.user));
}

export function clearAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
  localStorage.removeItem(USER);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}
