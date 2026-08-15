import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  BrokerCatalogItem,
  BrokerStatePublic,
  CaptchaQueueItem,
  FreezeChecklistItem,
  GeneratedRequest,
  RemediationJob,
} from "@/lib/types";

export function useBrokerCatalog() {
  return useQuery({
    queryKey: ["remediation", "brokers"],
    queryFn: () =>
      api.get<{
        brokers: BrokerCatalogItem[];
        attribution: string;
      }>("/remediation/brokers"),
  });
}

export function useBrokerStates() {
  return useQuery({
    queryKey: ["remediation", "state"],
    queryFn: () => api.get<BrokerStatePublic[]>("/remediation/state"),
  });
}

export function useRemediationJobs() {
  return useQuery({
    queryKey: ["remediation", "jobs"],
    queryFn: () => api.get<RemediationJob[]>("/remediation/jobs"),
    refetchInterval: 5000,
  });
}

export function useRemediationJob(jobId?: string) {
  return useQuery({
    queryKey: ["remediation", "jobs", jobId],
    enabled: !!jobId,
    queryFn: () => api.get<RemediationJob>(`/remediation/jobs/${jobId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (
        status &&
        ["completed", "partial", "failed", "cancelled", "timed_out"].includes(status)
      ) {
        return false;
      }
      return 5000;
    },
  });
}

export function useStartBrokerOptOut() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      identifier_id: string;
      broker_ids?: string[];
      dry_run: boolean;
      profile?: {
        display_name?: string;
        state?: string;
        city?: string;
        zip?: string;
      };
    }) =>
      api.post<RemediationJob>("/remediation/jobs/broker-optout", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useCancelRemediationJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) =>
      api.post<RemediationJob>(`/remediation/jobs/${jobId}/cancel`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useCaptchaQueue() {
  return useQuery({
    queryKey: ["remediation", "captcha"],
    queryFn: () => api.get<CaptchaQueueItem[]>("/remediation/captcha"),
    refetchInterval: 5000,
  });
}

export function useSolveCaptcha() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      action,
      solution_token,
    }: {
      id: string;
      action: "solve" | "skip" | "manual_done";
      solution_token?: string;
    }) =>
      api.post(`/remediation/captcha/${id}`, {
        action,
        solution_token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}

export function useFreezeChecklist() {
  return useQuery({
    queryKey: ["remediation", "freeze"],
    queryFn: () => api.get<FreezeChecklistItem[]>("/remediation/freeze"),
  });
}

export function useUpdateFreezeItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
      notes,
    }: {
      id: string;
      status: string;
      notes?: string;
    }) =>
      api.patch<FreezeChecklistItem>(`/remediation/freeze/${id}`, {
        status,
        notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "freeze"] });
    },
  });
}

export function useGeneratedRequests() {
  return useQuery({
    queryKey: ["remediation", "requests"],
    queryFn: () => api.get<GeneratedRequest[]>("/remediation/requests"),
  });
}

export function useCreateKnowRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      regime: "ccpa" | "gdpr" | "other";
      recipient_name: string;
      recipient_email?: string;
      identifier_id?: string;
      include_deletion: boolean;
    }) => api.post<GeneratedRequest>("/remediation/know", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useCreateComplaint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      regime: "ccpa" | "gdpr" | "other";
      recipient_name: string;
      regulator: string;
      facts: string;
    }) => api.post<GeneratedRequest>("/remediation/complaints", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useMarkRequestSent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      api.post<GeneratedRequest>(`/remediation/requests/${id}/mark-sent`, {
        sent: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation", "requests"] });
    },
  });
}

export function useVerifyBrokers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (broker_ids?: string[]) =>
      api.post("/remediation/verify", { broker_ids }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["remediation"] });
    },
  });
}
