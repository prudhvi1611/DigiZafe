import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ScanPublic, ExposureLayer } from "@/lib/types";

export function useScans() {
  return useQuery({
    queryKey: ["scans"],
    queryFn: () => api.get<ScanPublic[]>("/scans"),
  });
}

export function useScan(id: string | undefined) {
  return useQuery({
    queryKey: ["scans", id],
    enabled: !!id,
    queryFn: () => api.get<ScanPublic>(`/scans/${id}`),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      if (s && ["completed", "partial", "failed", "cancelled", "timed_out"].includes(s)) return false;
      return 3000;
    },
  });
}

export function useCreateScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { identifier_id: string; connector_ids?: string[]; layer_scope: ExposureLayer }) =>
      api.post<ScanPublic>("/scans", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
}

export function useCancelScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ScanPublic>(`/scans/${id}/cancel`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
}
