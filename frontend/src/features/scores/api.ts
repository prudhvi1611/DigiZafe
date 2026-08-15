import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScorePublic } from "@/lib/types";

export function useLatestScore(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["scores", "latest", identifierId || "all"],
    queryFn: () => api.get<ScorePublic>(`/scores/latest${q}`),
    retry: false,
  });
}

export function useComputeScore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id?: string; persist?: boolean }) =>
      api.post<ScorePublic>("/scores/compute", { persist: true, trigger: "manual", ...body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scores"] });
    },
  });
}

export function useScoreHistory(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["scores", "history", identifierId || "all"],
    queryFn: () =>
      api.get<{ id: string; score_combined: number; severity: string; created_at: string; trigger: string }[]>(
        `/scores/history${q}`
      ),
  });
}
