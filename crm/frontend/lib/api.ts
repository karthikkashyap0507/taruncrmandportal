import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_CRM_API_URL || "http://localhost:8001";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("crm_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      const refreshToken = localStorage.getItem("crm_refresh_token");
      if (refreshToken) {
        try {
          const res = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem("crm_access_token", res.data.access_token);
          localStorage.setItem("crm_refresh_token", res.data.refresh_token);
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api.request(error.config);
        } catch {
          localStorage.removeItem("crm_access_token");
          localStorage.removeItem("crm_refresh_token");
          window.location.href = "/login";
        }
      } else {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (credential: string, password: string) =>
    api.post("/auth/login", { credential, password }),
  register: (data: object) => api.post("/auth/register", data),
  logout: (refresh_token: string) => api.post("/auth/logout", { refresh_token }),
  forgotPassword: (email: string) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }),
  me: () => api.get("/users/me"),
};

// Users
export const usersApi = {
  list: (params?: object) => api.get("/users", { params }),
  create: (data: object) => api.post("/users", data),
  get: (id: number) => api.get(`/users/${id}`),
  update: (id: number, data: object) => api.put(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  activity: (id: number) => api.get(`/users/${id}/activity`),
};

// Leads
export const leadsApi = {
  list: (params?: object) => api.get("/leads", { params }),
  pipeline: () => api.get("/leads/pipeline"),
  create: (data: object) => api.post("/leads", data),
  get: (id: number) => api.get(`/leads/${id}`),
  update: (id: number, data: object) => api.put(`/leads/${id}`, data),
  updateStatus: (id: number, status: string) =>
    api.patch(`/leads/${id}/status`, null, { params: { status } }),
  delete: (id: number) => api.delete(`/leads/${id}`),
  addNote: (id: number, content: string) => api.post(`/leads/${id}/notes`, { content }),
  getNotes: (id: number) => api.get(`/leads/${id}/notes`),
  addFollowup: (id: number, data: object) => api.post(`/leads/${id}/followups`, data),
  getFollowups: (id: number) => api.get(`/leads/${id}/followups`),
  completeFollowup: (leadId: number, fupId: number) =>
    api.patch(`/leads/${leadId}/followups/${fupId}/complete`),
};

// Clients
export const clientsApi = {
  list: (params?: object) => api.get("/clients", { params }),
  create: (data: object) => api.post("/clients", data),
  get: (id: number) => api.get(`/clients/${id}`),
  update: (id: number, data: object) => api.put(`/clients/${id}`, data),
  delete: (id: number) => api.delete(`/clients/${id}`),
  addContact: (companyId: number, data: object) =>
    api.post(`/clients/${companyId}/contacts`, data),
  updateContact: (contactId: number, data: object) =>
    api.put(`/clients/contacts/${contactId}`, data),
  deleteContact: (contactId: number) =>
    api.delete(`/clients/contacts/${contactId}`),
};

// Candidates
export const candidatesApi = {
  list: (params?: object) => api.get("/candidates", { params }),
  create: (data: object) => api.post("/candidates", data),
  get: (id: number) => api.get(`/candidates/${id}`),
  update: (id: number, data: object) => api.put(`/candidates/${id}`, data),
  delete: (id: number) => api.delete(`/candidates/${id}`),
  uploadResume: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(`/candidates/${id}/resume`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  computeAts: (id: number, skills: string[], exp: number) =>
    api.post(`/candidates/${id}/ats-score`, skills, { params: { required_experience: exp } }),
  addNote: (id: number, content: string, type?: string) =>
    api.post(`/candidates/${id}/notes`, { content, type }),
  getNotes: (id: number) => api.get(`/candidates/${id}/notes`),
};

// Jobs
export const jobsApi = {
  list: (params?: object) => api.get("/jobs", { params }),
  create: (data: object) => api.post("/jobs", data),
  get: (id: number) => api.get(`/jobs/${id}`),
  update: (id: number, data: object) => api.put(`/jobs/${id}`, data),
  delete: (id: number) => api.delete(`/jobs/${id}`),
  addApplication: (jobId: number, data: object) =>
    api.post(`/jobs/${jobId}/applications`, data),
  updateStage: (jobId: number, appId: number, stage: string) =>
    api.patch(`/jobs/${jobId}/applications/${appId}/stage`, null, { params: { stage } }),
};

// Interviews
export const interviewsApi = {
  list: () => api.get("/jobs/interviews/all"),
  schedule: (data: object) => api.post("/jobs/interviews", data),
  update: (id: number, data: object) => api.patch(`/jobs/interviews/${id}`, null, { params: data }),
};

// Analytics
export const analyticsApi = {
  overview: () => api.get("/analytics/overview"),
  leadsPipeline: () => api.get("/analytics/leads/pipeline"),
  leadsTrend: (days?: number) => api.get("/analytics/leads/trend", { params: { days } }),
  candidatesByStatus: () => api.get("/analytics/candidates/by-status"),
  teamPerformance: (days?: number) => api.get("/analytics/team/performance", { params: { days } }),
  revenue: () => api.get("/analytics/revenue"),
};

// Tasks
export const tasksApi = {
  list: (params?: object) => api.get("/tasks", { params }),
  create: (data: object) => api.post("/tasks", data),
  update: (id: number, data: object) => api.put(`/tasks/${id}`, data),
  delete: (id: number) => api.delete(`/tasks/${id}`),
};

// Notifications
export const notificationsApi = {
  list: (unreadOnly?: boolean) =>
    api.get("/notifications", { params: { unread_only: unreadOnly } }),
  unreadCount: () => api.get("/notifications/unread-count"),
  markRead: (id: number) => api.patch(`/notifications/${id}/read`),
  markAllRead: () => api.patch("/notifications/read-all"),
};
