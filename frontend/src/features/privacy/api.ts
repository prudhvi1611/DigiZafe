import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AuditEvent,
  ConsentItem,
  EgressEvent,
  ExportJob,
  ExportPackageResponse,
} from "@/lib/types";

export function useConsent() {
  return useQuery({
    queryKey: ["privacy", "consent"],
    queryFn: () => api.get<ConsentItem[]>("/privacy/consent"),
  });
}

export function useGrantConsent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      purpose: string;
      scope?: string;
      details?: Record<string, unknown>;
    }) => api.post("/privacy/consent", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "consent"] });
    },
  });
}

export function useRevokeConsent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (purpose: string) =>
      api.post("/privacy/consent/revoke", { purpose }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "consent"] });
    },
  });
}

export function useAuditEvents() {
  return useQuery({
    queryKey: ["privacy", "audit"],
    queryFn: () => api.get<AuditEvent[]>("/privacy/audit?limit=100"),
  });
}

export function useEgressEvents() {
  return useQuery({
    queryKey: ["privacy", "egress"],
    queryFn: () => api.get<EgressEvent[]>("/privacy/egress?limit=100"),
  });
}

export function useCreateExport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      include_audit: boolean;
      include_egress: boolean;
    }) => api.post<ExportJob>("/privacy/export", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["privacy", "exports"] });
    },
  });
}

export function useExportPackage(exportId?: string) {
  return useQuery({
    queryKey: ["privacy", "exports", exportId],
    enabled: !!exportId,
    queryFn: () =>
      api.get<ExportPackageResponse>(`/privacy/export/${exportId}`),
  });
}

export function useRequestAccountDeletion() {
  return useMutation({
    mutationFn: (body: {
      confirm_phrase: string;
      immediate: boolean;
    }) =>
      api.post("/privacy/account/delete", body),
  });
}
