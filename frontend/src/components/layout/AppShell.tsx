import * as React from "react";
import { Link, NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Fingerprint,
  Radar,
  AlertTriangle,
  Gauge,
  ListChecks,
  Network,
  LogOut,
  Shield,
  UserRoundCog,
  LockKeyhole,
  Rocket,
  Activity,
  ChevronRight,
  ShieldCheck,
  Menu,
  X,
  Radio,
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/app/onboarding", label: "Start here", icon: Rocket, badge: "NEW" },
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/identifiers", label: "Identifiers", icon: Fingerprint },
  { to: "/app/scans", label: "Scans", icon: Radar },
  { to: "/app/findings", label: "Findings", icon: AlertTriangle },
  { to: "/app/scores", label: "PDSS Score", icon: Gauge },
  { to: "/app/recommendations", label: "Plan", icon: ListChecks },
  { to: "/app/remediation", label: "Remediation", icon: UserRoundCog },
  { to: "/app/identity", label: "Identity graph", icon: Network },
  { to: "/app/privacy", label: "Privacy center", icon: LockKeyhole },
  { to: "/app/timeline", label: "Timeline", icon: Activity },
  { to: "/app/reviews", label: "Reviews", icon: ListChecks },
];

export function AppShell() {
  const user = useAuthStore((state) => state.user);
  const clear = useAuthStore((state) => state.clear);
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const attribution = import.meta.env.VITE_XPOSEDORNOT_ATTRIBUTION as string | undefined;

  const currentNavItem = nav.find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
  );

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:border focus:border-cyan-500/40 focus:bg-slate-900 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-cyan-300 focus:shadow-[0_0_20px_rgba(6,182,212,0.4)]"
      >
        Skip to main content
      </a>

      {/* Desktop SOC Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-white/10 bg-gradient-to-b from-slate-900/90 via-slate-900/80 to-slate-950/95 backdrop-blur-xl md:flex md:flex-col shadow-2xl z-20">
        <div className="flex flex-col border-b border-white/10 p-4">
          <Link to="/app" className="flex items-center gap-3 group">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/30 bg-gradient-to-b from-cyan-500/20 to-transparent shadow-[0_0_15px_rgba(6,182,212,0.25)] transition-all group-hover:scale-105 group-hover:border-cyan-500/50">
              <Shield className="h-5 w-5 text-cyan-400 group-hover:drop-shadow-[0_0_8px_rgba(6,182,212,0.8)] transition-all" />
              <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-400" />
              </span>
            </div>
            <div>
              <div className="font-bold tracking-tight text-white text-base flex items-center gap-1.5">
                DigiZafe
                <span className="rounded bg-cyan-500/20 border border-cyan-500/30 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-cyan-300 uppercase">
                  v1.0
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono tracking-wider uppercase">Exposure Intelligence</div>
            </div>
          </Link>

          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
              <span className="text-[11px] font-medium text-slate-300">Zero-Egress Mode</span>
            </div>
            <StatusBadge status="active" label="SECURE" className="py-0 text-[10px]" />
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4" aria-label="Main navigation">
          <div className="px-3 pb-2 text-[10px] font-mono font-bold tracking-wider uppercase text-slate-400">
            Operations Console
          </div>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center justify-between rounded-lg px-3 py-2.5 text-xs font-medium transition-all duration-200",
                  isActive
                    ? "bg-gradient-to-r from-cyan-500/20 via-cyan-500/10 to-transparent text-cyan-300 border-l-2 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)]"
                    : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
                )
              }
            >
              <div className="flex items-center gap-3">
                <item.icon className="h-4 w-4 shrink-0 transition-transform duration-200 group-hover:scale-110" aria-hidden="true" />
                <span className="truncate">{item.label}</span>
              </div>
              <div className="flex items-center gap-1">
                {item.badge && (
                  <span className="rounded-full bg-cyan-500/20 border border-cyan-500/40 px-1.5 py-0.5 text-[9px] font-mono font-bold text-cyan-300">
                    {item.badge}
                  </span>
                )}
                <ChevronRight className="h-3 w-3 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 text-slate-500" />
              </div>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 bg-slate-950/80 p-4">
          <div className="mb-3 flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.03] p-2.5 shadow-inner">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 font-bold text-xs font-mono">
              {user?.email?.charAt(0).toUpperCase() || "A"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold text-slate-200" title={user?.email || undefined}>
                {user?.email || "Authenticated Analyst"}
              </div>
              <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                <ShieldCheck className="h-3 w-3 inline" /> Local Enclave Active
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full justify-center border-white/10 bg-white/5 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/30 transition-all"
            onClick={() => {
              clear();
              navigate("/login");
            }}
          >
            <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile Header */}
        <header className="sticky top-0 z-50 flex items-center justify-between border-b border-white/10 bg-slate-900/95 px-4 py-3 backdrop-blur-md md:hidden">
          <Link to="/app" className="flex items-center gap-2 font-bold text-white">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/20">
              <Shield className="h-4 w-4 text-cyan-400" aria-hidden="true" />
            </div>
            <span>DigiZafe</span>
          </Link>

          <div className="flex items-center gap-2">
            <StatusBadge status="secure" label="LOCAL" pulse={false} className="py-0" />
            <Button
              variant="ghost"
              size="sm"
              className="px-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </Button>
          </div>
        </header>

        {/* Mobile Nav Overflow */}
        <div className="flex gap-1.5 overflow-x-auto border-b border-white/10 bg-slate-900/80 p-2 md:hidden scrollbar-none" aria-label="Mobile navigation">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          <Button
            variant="ghost"
            size="sm"
            className="whitespace-nowrap text-xs text-red-400 hover:bg-red-500/10 px-3 py-1.5 h-auto"
            onClick={() => {
              clear();
              navigate("/login");
            }}
          >
            Sign out
          </Button>
        </div>

        {/* Top SOC Status Bar (Desktop Only) */}
        <div className="hidden border-b border-white/10 bg-gradient-to-r from-slate-900/60 via-slate-900/30 to-slate-950 px-8 py-3 md:flex md:items-center md:justify-between">
          <div className="flex items-center gap-3 text-xs text-slate-300 font-mono">
            <span className="flex items-center gap-1.5 font-semibold text-white uppercase tracking-wider">
              {currentNavItem ? currentNavItem.label : "Console"}
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-slate-400">Cryptographic Boundary: Personal Enclave</span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Egress Protection: ACTIVE
            </span>
            <span className="h-3 w-px bg-white/10" />
            <span>Telemetry: DISABLED</span>
          </div>
        </div>

        <main id="main-content" className="flex-1 overflow-auto p-4 sm:p-6 md:p-8 relative">
          {/* Subtle Ambient Radial Grid Pattern */}
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] opacity-20 z-0" />
          <div className="relative z-10 mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>

        <footer className="border-t border-white/10 bg-slate-950 px-4 py-3 text-center text-xs font-mono text-slate-500 transition-colors hover:text-slate-400">
          <div className="mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>
              {attribution || "Free-path breach data: XposedOrNot — personal use; respect ToS."}
            </div>
            <div className="flex items-center gap-2 font-semibold text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5 text-cyan-400 inline" /> Self-only verified identifiers (G1)
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
