import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IdentityGraphPublic } from "@/lib/types";

export function useIdentityGraph() {
  return useQuery({
    queryKey: ["identity", "graph"],
    queryFn: () => api.get<IdentityGraphPublic>("/identity/graph"),
  });
}

export function useRebuildGraph() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<IdentityGraphPublic>("/identity/graph/rebuild"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity"] }),
  });
}

export function useIdentityAnchor() {
  return useQuery({
    queryKey: ["identity", "anchor"],
    queryFn: async () => {
      const res = await api.get<any>("/identity/anchor");
      return res.data;
    },
  });
}

export function useCandidateDiscoveryRuns() {
  return useQuery({
    queryKey: ["identity", "discovery_runs"],
    queryFn: async () => {
      const res = await api.get("/identity/discovery/runs");
      return (res as any).data;
    },
  });
}

export function useCandidateProfiles() {
  return useQuery({
    queryKey: ["identity", "candidates"],
    queryFn: async () => {
      const res = await api.get("/identity/discovery/candidates");
      return (res as any).data;
    },
  });
}

export function useAddAlias() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { alias_type: string; value: string }) => api.post("/identity/aliases", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity", "anchor"] }),
  });
}

export function useRevokeAlias() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (aliasId: string) => api.post(`/identity/aliases/${aliasId}/revoke`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity", "anchor"] }),
  });
}

export function useAddProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { platform: string; profile_url: string; username_hint?: string }) => 
      api.post("/identity/profiles", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity", "anchor"] }),
  });
}

export function useRevokeProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => api.post(`/identity/profiles/${profileId}/revoke`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity", "anchor"] }),
  });
}

export function useStartDiscovery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (inputIds?: string[]) => {
      await api.post("/identity/discovery/orchestrate", { identity_input_ids: inputIds });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["identity", "discovery_runs"] });
      qc.invalidateQueries({ queryKey: ["identity", "orchestration_runs"] });
    },
  });
}

export function useOrchestrationRuns() {
  return useQuery({
    queryKey: ["identity", "orchestration_runs"],
    queryFn: async () => {
      const res = await api.get("/identity/discovery/orchestration/runs");
      return (res as any).data;
    },
  });
}

export function useConfirmCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (candidateId: string) => {
      await api.post(`/identity/discovery/candidates/${candidateId}/confirm`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["identity", "candidates"] });
      qc.invalidateQueries({ queryKey: ["identity", "anchor"] });
    },
  });
}

export function useDismissCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (candidateId: string) => {
      await api.post(`/identity/discovery/candidates/${candidateId}/dismiss`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identity", "candidates"] }),
  });
}

export function useIdentityAssessment(candidateId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["identity", "assessment", candidateId],
    queryFn: async () => {
      const res = await api.get(`/identity/candidates/${candidateId}/assessment`);
      return (res as any).data;
    },
    enabled: !!candidateId && enabled,
    retry: false,
  });
}

export function useRecalculateAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (candidateId: string) => {
      const res = await api.post(`/identity/candidates/${candidateId}/assessment/recalculate`);
      return (res as any).data;
    },
    onSuccess: (_, candidateId) => {
      qc.invalidateQueries({ queryKey: ["identity", "assessment", candidateId] });
    },
  });
}
