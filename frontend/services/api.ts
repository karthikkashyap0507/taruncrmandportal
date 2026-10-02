import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "@/lib/constants";
import type { AuthSuccess } from "@/lib/auth-storage";
import {
  clearAuth,
  getAccessToken,
  getRefreshToken,
  persistAuth,
} from "@/lib/auth-storage";
import type {
  AppMessage,
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  ATSResult,
  Candidate,
  CandidateUpdate,
  Company,
  ExternalJob,
  Job,
  JobCreate,
  JobUpdate,
  MessageType,
  Recruiter,
  SavedJob,
} from "@/types";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Private files (resumes) come back from the API as short-lived signed paths
export const fileUrl = (path?: string | null) =>
  path ? (path.startsWith("http") ? path : `${API_BASE_URL.replace(/\/api\/v1\/?$/, "")}${path}`) : undefined;

// Readable error text from an API failure
export const apiError = (e: unknown, fallback = "Something went wrong") => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
};

let refreshPromise: Promise<void> | null = null;

async function refreshAccessToken(): Promise<void> {
  const rt = getRefreshToken();
  if (!rt) {
    clearAuth();
    throw new Error("No refresh token");
  }
  const { data } = await axios.post<{
    access_token: string;
    refresh_token: string;
    token_type: string;
    user: { id: number; name: string; email: string; role: string };
  }>(`${API_BASE_URL}/auth/refresh`, { refresh_token: rt });
  persistAuth(data as AuthSuccess);
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    if (
      status === 401 &&
      original &&
      !original._retry &&
      !original.url?.includes("/auth/login") &&
      !original.url?.includes("/auth/register") &&
      !original.url?.includes("/auth/refresh")
    ) {
      // Only attempt refresh if we actually have a stored token (i.e. user was logged in)
      if (!getAccessToken() && !getRefreshToken()) {
        // Unauthenticated visitor hitting a protected endpoint — just reject silently
        return Promise.reject(error);
      }
      original._retry = true;
      try {
        if (!refreshPromise) {
          refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
        }
        await refreshPromise;
        const token = getAccessToken();
        if (token) original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        clearAuth();
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth")) {
          window.location.href = "/auth/signin";
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

// Jobs API
export const jobsApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    api.get<Job[]>("/jobs", { params }),
  get: (id: number) => api.get<Job>(`/jobs/${id}`),
  create: (data: JobCreate) => api.post<Job>("/jobs", data),
  update: (id: number, data: JobUpdate) => api.patch<Job>(`/jobs/${id}`, data),
  delete: (id: number) => api.delete(`/jobs/${id}`),
  apply: (id: number, data?: ApplicationCreate) => api.post(`/jobs/${id}/apply`, data || {}),
  listMy: () => api.get<Job[]>("/jobs/recruiter/my"),
  getMyCompany: () => api.get<Company>("/jobs/recruiter/company"),
  listApplications: (jobId: number) => api.get<Application[]>(`/jobs/${jobId}/applications`),
  updateApplication: (appId: number, data: ApplicationUpdate) =>
    api.patch<Application>(`/jobs/applications/${appId}`, data),
  listMyApplications: () => api.get<Application[]>("/jobs/candidate/my-applications"),
  computeATS: (jobId: number, appId: number) =>
    api.post(`/jobs/${jobId}/applications/${appId}/compute-ats`),
  computeATSAll: (jobId: number) =>
    api.post<{ computed: number; results: ATSResult[] }>(`/jobs/${jobId}/compute-ats-all`),
};

// Saved Jobs API
export const savedJobsApi = {
  list: () => api.get<SavedJob[]>("/saved-jobs"),
  save: (jobId: number) => api.post(`/saved-jobs/${jobId}`),
  unsave: (jobId: number) => api.delete(`/saved-jobs/${jobId}`),
  check: (jobId: number) => api.get<{ saved: boolean }>(`/saved-jobs/check/${jobId}`),
};

// External / AI search
export const externalJobsApi = {
  search: (params?: { q?: string; location?: string; employment_type?: string; salary_min?: number }) =>
    api.get<{ internal: Job[]; external: ExternalJob[]; total: number }>("/external/jobs", { params }),
  recommendations: () => api.get<Job[]>("/external/recommendations"),
};

// Profiles API
export const profilesApi = {
  getMyProfile: () => api.get<Candidate | Recruiter>("/profiles/me"),
  getCandidateProfile: () => api.get<Candidate>("/profiles/candidate/me"),
  updateCandidateProfile: (data: CandidateUpdate) =>
    api.patch<Candidate>("/profiles/candidate/me", data),
  getRecruiterProfile: () => api.get<Recruiter>("/profiles/recruiter/me"),
};

// Upload API
export const uploadApi = {
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<{ url: string; filename: string; message: string }>("/upload/resume", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<{ url: string; filename: string; message: string }>("/upload/avatar", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

// Messages API
export const messagesApi = {
  send: (applicationId: number, content: string, messageType: MessageType = "message") =>
    api.post<AppMessage>(`/messages/applications/${applicationId}`, { content, message_type: messageType }),
  getForApplication: (applicationId: number) =>
    api.get<AppMessage[]>(`/messages/applications/${applicationId}`),
  getInbox: () => api.get<AppMessage[]>("/messages/candidate/inbox"),
};

// Admin API
export const adminApi = {
  getStats: () => api.get("/admin/stats"),
  listUsers: (params?: { skip?: number; limit?: number; role?: string; include_inactive?: boolean }) =>
    api.get("/admin/users", { params }),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
  activateUser: (id: number) => api.post(`/admin/users/${id}/activate`),
  unlockUser: (id: number) => api.post(`/admin/users/${id}/unlock`),
  listCompanies: (params?: { skip?: number; limit?: number }) => api.get("/admin/companies", { params }),
  deleteCompany: (id: number) => api.delete(`/admin/companies/${id}`),
  listJobs: (params?: { status?: string; plan?: string; skip?: number; limit?: number }) => api.get("/admin/jobs", { params }),
  approveJob: (id: number) => api.post(`/admin/jobs/${id}/approve`),
  rejectJob: (id: number, reason: string) => api.post(`/admin/jobs/${id}/reject`, { reason }),
  setJobPremium: (id: number, is_premium: boolean) => api.post(`/admin/jobs/${id}/premium`, { is_premium }),
  updateJobStatus: (id: number, status: string) =>
    api.patch(`/admin/jobs/${id}/status`, null, { params: { status } }),
  auditLogs: (params?: { action?: string; skip?: number; limit?: number }) => api.get("/admin/audit-logs", { params }),
  emails: (params?: { status?: string; skip?: number; limit?: number }) => api.get("/admin/notifications", { params }),
  retryEmail: (id: number) => api.post(`/admin/notifications/${id}/retry`),
  retryFailedEmails: () => api.post("/admin/notifications/retry-failed"),
  enquiries: (params?: { status?: string; skip?: number; limit?: number }) => api.get("/admin/enquiries", { params }),
  markEnquiryHandled: (id: number) => api.post(`/admin/enquiries/${id}/handled`),
  reopenEnquiry: (id: number) => api.post(`/admin/enquiries/${id}/reopen`),
  subscribers: (params?: { status?: string; skip?: number; limit?: number }) => api.get("/admin/newsletter", { params }),
  sendDigestNow: () => api.post("/admin/newsletter/send-digest"),
};

// Public website forms (no login needed)
export const publicApi = {
  contact: (data: { name: string; email: string; subject: string; message: string }) =>
    api.post<{ id: number; message: string }>("/contact", data),
  subscribe: (email: string) =>
    api.post<{ status: "pending" | "subscribed"; message: string }>("/newsletter/subscribe", { email }),
  confirmSubscription: (email: string, sig: string) =>
    api.post<{ message: string }>("/newsletter/confirm", { email, sig }),
  unsubscribe: (email: string, sig: string) => api.post<{ message: string }>("/newsletter/unsubscribe", { email, sig }),
};
