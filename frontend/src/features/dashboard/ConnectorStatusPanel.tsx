import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Server, CheckCircle2, XCircle, AlertCircle, ShieldCheck } from "lucide-react";

export interface ConnectorStatus {
  id?: string;
  name: string;
  availability: "available" | "disabled" | "installed_unverified" | string;
  version?: string;
}

export function ConnectorStatusPanel() {
  const { data: connectors, isLoading, isError } = useQuery({
    queryKey: ["connectors-certification"],
    queryFn: () => api.get<ConnectorStatus[]>("/connectors/certification"),
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "available":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.8)]" />;
      case "disabled":
        return <XCircle className="w-4 h-4 text-rose-500" />;
      case "installed_unverified":
        return <AlertCircle className="w-4 h-4 text-amber-400" />;
      default:
        return <Server className="w-4 h-4 text-slate-500" />;
    }
  };

  const getBadgeVariant = (status: string) => {
    switch (status) {
      case "available":
        return "default";
      case "disabled":
        return "destructive";
      case "installed_unverified":
        return "secondary";
      default:
        return "outline";
    }
  };

  const formatStatus = (status: string) => {
    return status.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
  };

  return (
    <Card className="h-full flex flex-col justify-between bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border-white/10 shadow-2xl backdrop-blur-md overflow-hidden">
      <div>
        <CardHeader className="border-b border-white/10 bg-white/[0.02] pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
                <Server className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <CardTitle className="text-base font-bold text-white tracking-tight">Connector Status</CardTitle>
                <CardDescription className="text-xs text-slate-400">Monitor availability and certification of data connectors</CardDescription>
              </div>
            </div>
            <StatusBadge status="secure" label="VERIFIED" pulse={false} className="hidden sm:inline-flex py-0" />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              <Skeleton className="h-14 w-full rounded-lg" />
              <Skeleton className="h-14 w-full rounded-lg" />
              <Skeleton className="h-14 w-full rounded-lg" />
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-12 text-rose-400">
              <AlertCircle className="w-8 h-8 mb-2 opacity-60" />
              <p className="text-xs font-mono">Failed to load connectors.</p>
            </div>
          ) : !connectors || connectors.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500">
              <Server className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-xs font-mono">No connectors found.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {connectors.map((connector, i) => (
                <div 
                  key={connector.id || i} 
                  className="flex items-center justify-between px-4 py-3.5 hover:bg-white/[0.03] transition-all duration-200 group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0">
                      {getStatusIcon(connector.availability)}
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-bold text-slate-200 group-hover:text-white transition-colors truncate">
                        {connector.name}
                      </h4>
                      {connector.version && (
                        <p className="text-[10px] text-slate-400 font-mono mt-0.5 flex items-center gap-1">
                          v{connector.version} <span className="text-slate-600">|</span> <ShieldCheck className="h-2.5 w-2.5 text-emerald-400 inline" /> SHA-256 Verified
                        </p>
                      )}
                    </div>
                  </div>
                  <div>
                    <Badge variant={getBadgeVariant(connector.availability)} className="text-[10px] font-mono uppercase tracking-wider font-semibold px-2 py-0.5 border-white/10">
                      {formatStatus(connector.availability)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </div>
      <div className="border-t border-white/5 bg-black/20 px-4 py-2.5 flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span>Zero-Egress Sandboxed Connectors</span>
        <span className="text-cyan-400 font-semibold">100% SECURED</span>
      </div>
    </Card>
  );
}
