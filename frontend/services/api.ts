import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "@/lib/constants";
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
  persistAuth(data);
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
  list: (params?: { q?: string; location?: string; employment_type?: string; experience_level?: string; salary_min?: number; salary_max?: number; remote?: boolean }) =>
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
  listUsers: (params?: { skip?: number; limit?: number; role?: string }) =>
    api.get("/admin/users", { params }),
  deleteUser: (id: number) => api.delete(`/admin/users/${id}`),
  listCompanies: () => api.get("/admin/companies"),
  deleteCompany: (id: number) => api.delete(`/admin/companies/${id}`),
  listJobs: () => api.get("/admin/jobs"),
  updateJobStatus: (id: number, status: string) =>
    api.patch(`/admin/jobs/${id}/status`, null, { params: { status } }),
};
