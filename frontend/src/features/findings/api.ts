import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FindingPublic } from "@/lib/types";

export function useFindings(identifierId?: string) {
  const q = identifierId ? `?identifier_id=${encodeURIComponent(identifierId)}` : "";
  return useQuery({
    queryKey: ["findings", identifierId || "all"],
    queryFn: () => api.get<FindingPublic[]>(`/findings${q}`),
  });
}
