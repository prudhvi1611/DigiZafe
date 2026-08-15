import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PlanPublic, RecommendationPublic } from "@/lib/types";

export function useLatestPlan(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["recommendations", "latest", identifierId || "all"],
    queryFn: () => api.get<PlanPublic>(`/recommendations/latest${q}`),
    retry: false,
  });
}

export function useGeneratePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id?: string }) =>
      api.post<PlanPublic>("/recommendations/generate", { persist: true, ...body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}

export function useUpdateRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch<RecommendationPublic>(`/recommendations/${id}`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}
