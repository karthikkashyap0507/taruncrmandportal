import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CRMUser {
  id: number;
  name: string;
  email: string;
  phone?: string;
  role: "owner" | "bdm" | "hr";
  avatar_url?: string;
  permissions: Record<string, boolean>;
}

interface AuthState {
  user: CRMUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (user: CRMUser, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  isOwner: () => boolean;
  isBDM: () => boolean;
  isHR: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      setAuth: (user, accessToken, refreshToken) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("crm_access_token", accessToken);
          localStorage.setItem("crm_refresh_token", refreshToken);
        }
        set({ user, accessToken, refreshToken });
      },

      clearAuth: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("crm_access_token");
          localStorage.removeItem("crm_refresh_token");
        }
        set({ user: null, accessToken: null, refreshToken: null });
      },

      isOwner: () => get().user?.role === "owner",
      isBDM: () => get().user?.role === "bdm",
      isHR: () => get().user?.role === "hr",
    }),
    {
      name: "crm-auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);
