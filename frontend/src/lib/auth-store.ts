import { create } from "zustand";
import type { UserPublic } from "./types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: UserPublic | null) => void;
  clear: () => void;
  hydrateFromSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,

  setTokens: (access, refresh) => {
    set({
      accessToken: access,
      refreshToken: refresh,
    });
  },

  setUser: (user) => set({ user }),

  clear: () =>
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
    }),

  hydrateFromSession: () => {
    // Intentionally empty.
    // Sprint 10 does not persist tokens in localStorage or sessionStorage.
  },
}));

export function getRefreshFromSession(): string | null {
  // Retained for API compatibility with Sprint 9.
  // No browser storage is used.
  return useAuthStore.getState().refreshToken;
}
