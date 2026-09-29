import { api } from "@/services/api";
import type { AuthSuccess, AuthUser } from "@/lib/auth-storage";
import type { UserRole } from "@/types";

export type RegisterBody = {
  name: string;
  email: string;
  password: string;
  role: UserRole;
  company_name?: string;
};

export async function loginRequest(email: string, password: string): Promise<AuthSuccess> {
  const { data } = await api.post<AuthSuccess>("/auth/login", { email, password });
  return data;
}

export async function registerRequest(body: RegisterBody): Promise<AuthSuccess> {
  const payload =
    body.role === "candidate"
      ? { name: body.name, email: body.email, password: body.password, role: body.role }
      : {
          name: body.name,
          email: body.email,
          password: body.password,
          role: body.role,
          company_name: body.company_name,
        };
  const { data } = await api.post<AuthSuccess>("/auth/register", payload);
  return data;
}

export async function refreshSession(refreshToken: string): Promise<AuthSuccess> {
  const { data } = await api.post<AuthSuccess>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/auth/me");
  return data;
}

export async function forgotPassword(email: string): Promise<{ message: string; reset_token?: string | null }> {
  const { data } = await api.post<{ message: string; reset_token?: string | null }>("/auth/forgot-password", {
    email,
  });
  return data;
}

export async function resetPassword(token: string, new_password: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>("/auth/reset-password", {
    token,
    new_password,
  });
  return data;
}
