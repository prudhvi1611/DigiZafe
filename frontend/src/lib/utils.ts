import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function severityColor(sev: string | undefined): string {
  const s = (sev || "info").toLowerCase();
  if (s === "critical") return "text-severity-critical";
  if (s === "high") return "text-severity-high";
  if (s === "medium") return "text-severity-medium";
  if (s === "low") return "text-severity-low";
  return "text-severity-none";
}

export function severityBg(sev: string | undefined): string {
  const s = (sev || "info").toLowerCase();
  if (s === "critical") return "bg-red-500/15 border-red-500/40";
  if (s === "high") return "bg-orange-500/15 border-orange-500/40";
  if (s === "medium") return "bg-yellow-500/15 border-yellow-500/40";
  if (s === "low") return "bg-green-500/15 border-green-500/40";
  return "bg-slate-500/15 border-slate-500/40";
}

export function redactEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain) return "***";
  if (local.length <= 2) return `${local[0]}***@${domain}`;
  return `${local.slice(0, 2)}***@${domain}`;
}

export function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
