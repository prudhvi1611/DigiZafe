import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { TokenPair, UserPublic } from "@/lib/types";

export function useMe(enabled = true) {
  const setUser = useAuthStore((s) => s.setUser);
  const access = useAuthStore((s) => s.accessToken);
  const refresh = useAuthStore((s) => s.refreshToken);

  return useQuery({
    queryKey: ["me"],
    enabled: enabled && !!(access || refresh),
    queryFn: async () => {
      const me = await api.get<UserPublic>("/auth/me");
      setUser(me);
      return me;
    },
    retry: false,
  });
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string; mfa_code?: string }) => {
      return api.post<TokenPair>("/auth/login/json", body, false);
    },
    onSuccess: async (data) => {
      if (data.mfa_required) return data;
      setTokens(data.access_token, data.refresh_token);
      await qc.invalidateQueries({ queryKey: ["me"] });
      return data;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api.post<UserPublic>("/auth/register", body, false),
  });
}
