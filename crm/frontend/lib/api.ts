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
  changePassword: (current_password: string, new_password: string) =>
    api.post("/auth/change-password", { current_password, new_password }),
  sessions: () => api.get("/auth/sessions"),
  revokeSession: (id: number) => api.delete(`/auth/sessions/${id}`),
  logoutAll: () => api.post("/auth/logout-all"),
};

// Users
export const usersApi = {
  list: (params?: object) => api.get("/users", { params }),
  create: (data: object) => api.post("/users", data),
  get: (id: number) => api.get(`/users/${id}`),
  update: (id: number, data: object) => api.put(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  activity: (id: number) => api.get(`/users/${id}/activity`),
  // Names + roles of active team members (any role; used for assignment dropdowns)
  directory: () => api.get("/users/directory"),
  updateMe: (data: object) => api.put("/users/me", data),
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
  revenueMonthly: (months?: number) => api.get("/analytics/revenue/monthly", { params: { months } }),
  placementsSummary: () => api.get("/analytics/placements/summary"),
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

// Private files (resumes, signed MOUs): the API returns short-lived signed paths
export const fileUrl = (path?: string | null) =>
  path ? (path.startsWith("http") ? path : `${BASE_URL}${path}`) : undefined;

// Readable error text from an API failure
export const apiError = (e: any, fallback = "Something went wrong") => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : fallback;
};

// MOUs / client agreements
export const agreementsApi = {
  list: (params?: object) => api.get("/agreements", { params }),
  get: (id: number) => api.get(`/agreements/${id}`),
  create: (data: object) => api.post("/agreements", data),
  update: (id: number, data: object) => api.put(`/agreements/${id}`, data),
  setStatus: (id: number, status: string) => api.post(`/agreements/${id}/status`, null, { params: { status } }),
  uploadDocument: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(`/agreements/${id}/document`, fd, { headers: { "Content-Type": "multipart/form-data" } });
  },
};

// Placements (offer -> joining)
export const placementsApi = {
  list: (params?: object) => api.get("/placements", { params }),
  get: (id: number) => api.get(`/placements/${id}`),
  create: (data: object) => api.post("/placements", data),
  update: (id: number, data: object) => api.put(`/placements/${id}`, data),
  setStatus: (id: number, status: string, date?: string, note?: string) =>
    api.post(`/placements/${id}/status`, { status, date, note }),
};

// Invoices
export const invoicesApi = {
  list: (params?: object) => api.get("/invoices", { params }),
  create: (data: object) => api.post("/invoices", data),
  markPaid: (id: number) => api.post(`/invoices/${id}/mark-paid`),
  cancel: (id: number, reason: string) => api.post(`/invoices/${id}/cancel`, { reason }),
};

// Incentives
export const incentivesApi = {
  list: (params?: object) => api.get("/incentives", { params }),
  summary: () => api.get("/incentives/summary"),
  rules: () => api.get("/incentives/rules"),
  updateRule: (role: string, percentage: number) => api.put(`/incentives/rules/${role}`, { percentage }),
  approve: (id: number) => api.post(`/incentives/${id}/approve`),
  markPaid: (id: number) => api.post(`/incentives/${id}/mark-paid`),
  void: (id: number, reason: string) => api.post(`/incentives/${id}/void`, { reason }),
};

// Owner tools: audit trail + email delivery log
export const auditApi = {
  logs: (params?: object) => api.get("/audit-logs", { params }),
  deliveries: (params?: object) => api.get("/notifications/deliveries", { params }),
  retryDelivery: (id: number) => api.post(`/notifications/deliveries/${id}/retry`),
  retryAllFailed: () => api.post("/notifications/deliveries/retry-failed"),
};

// CSV exports (downloaded with the user's token)
export const downloadReport = async (report: string) => {
  const res = await api.get(`/reports/${report}.csv`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${report}-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};

