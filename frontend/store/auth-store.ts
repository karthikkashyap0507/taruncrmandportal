import { create } from "zustand";
import type { AuthSuccess, AuthUser } from "@/lib/auth-storage";
import { clearAuth, getAccessToken, getStoredUser, persistAuth } from "@/lib/auth-storage";
import { API_BASE_URL } from "@/lib/constants";

type AuthState = {
  user: AuthUser | null;
  hydrated: boolean;
  setFromSuccess: (data: AuthSuccess) => void;
  setUser: (user: AuthUser | null) => void;
  hydrate: () => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  hydrated: false,
  setFromSuccess: (data) => {
    persistAuth(data);
    set({ user: data.user, hydrated: true });
  },
  setUser: (user) => set({ user }),
  hydrate: () => {
    set({ user: getStoredUser(), hydrated: true });
  },
  logout: () => {
    // End the session on the server too (best effort), so the token stops working everywhere
    const token = getAccessToken();
    if (token) {
      fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    }
    clearAuth();
    set({ user: null, hydrated: true });
  },
}));
