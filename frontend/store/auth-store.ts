import { create } from "zustand";
import type { AuthSuccess, AuthUser } from "@/lib/auth-storage";
import { clearAuth, getStoredUser, persistAuth } from "@/lib/auth-storage";

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
    clearAuth();
    set({ user: null, hydrated: true });
  },
}));
