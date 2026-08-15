import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LayerMetadata } from "@/lib/types";

export function useLayerCatalog() {
  return useQuery({
    queryKey: ["layers"],
    queryFn: () => api.get<LayerMetadata[]>("/layers"),
  });
}
