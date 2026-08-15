import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { IdentifierPublic, IdentifierType, VerificationStartResponse } from "@/lib/types";

export function useIdentifiers() {
  return useQuery({
    queryKey: ["identifiers"],
    queryFn: () => api.get<IdentifierPublic[]>("/identifiers"),
  });
}

export function useCreateIdentifier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { type: IdentifierType; value: string }) =>
      api.post<IdentifierPublic>("/identifiers", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}

export function useDeleteIdentifier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<{ message: string }>(`/identifiers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}

export function useStartVerify() {
  return useMutation({
    mutationFn: ({ id, method }: { id: string; method?: string }) => {
      const q = method ? `?method=${encodeURIComponent(method)}` : "";
      return api.post<VerificationStartResponse>(`/identifiers/${id}/verify/start${q}`);
    },
  });
}

export function useConfirmVerify() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      challenge_id,
      code,
    }: {
      id: string;
      challenge_id: string;
      code?: string;
    }) =>
      api.post(
        `/identifiers/${id}/verify/confirm?challenge_id=${encodeURIComponent(challenge_id)}`,
        { code }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["identifiers"] }),
  });
}
